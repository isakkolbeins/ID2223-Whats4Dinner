import modal

app = modal.App("whats4dinner_fineTuning")
image = modal.Image.from_registry("nvidia/cuda:12.4.0-devel-ubuntu22.04", add_python="3.11").apt_install("git").pip_install("unsloth")
vol = modal.Volume.from_name("model-checkpoints")

@app.function(image=image, gpu="A100-40GB:3", secrets=[modal.Secret.from_name("my-huggingface-secret")], timeout=3600, schedule=modal.Period(days=7), volumes={"/data": vol})
def main():
    from unsloth import FastLanguageModel, is_bfloat16_supported
    from datasets import Dataset, load_dataset
    from transformers import DataCollatorForSeq2Seq, TrainingArguments
    from trl import SFTTrainer
    from unsloth.chat_templates import standardize_sharegpt, train_on_responses_only
    import pandas as pd
    import ast
    import os
    from datetime import datetime

    print("Starting fine-tuning process...")

    # Get the current timestamp for dynamic naming
    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    checkpoint_dir = f"/checkpoints/checkpoints_{current_date}"
    model_save_dir = f"/models/model_{current_date}"

    # Configuration parameters
    MAX_SEQ_LENGTH = 2048
    DTYPE = None  # Auto detection. Float16 for Tesla T4, Bfloat16 for Ampere+
    LOAD_IN_4BIT = True  # Use 4bit quantization to reduce memory usage

    # Step 1: Load the pre-trained language model and tokenizer
    print("Loading model...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Llama-3.2-1B-Instruct",
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=DTYPE,
        load_in_4bit=LOAD_IN_4BIT,
    )

    # Step 2: Add LoRA adapters to the model
    print("Adding LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    # Step 3: Load and prepare the dataset
    print("Loading and preparing dataset...")
    dataset = load_dataset("kolbeins/recipe-training-5k-simpler", split="train")
    uploaded_dataset = load_dataset("kolbeins/uploaded-recipes", split="train")

    dataset_df = pd.DataFrame(dataset)
    uploaded_df = pd.DataFrame(uploaded_dataset)

    def create_dynamic_prompt(row):
        system_message = (
            "You are a recipe generator. Based on the inputs provided, generate a detailed "
            "and correctly formatted recipe that meets the user's needs. Follow the instructions carefully."
        )

        tags_list = ast.literal_eval(row["steps"])
        tags = ",".join(tags_list)
        servings = row["servings"]
        units = "Imperial"

        user_message = f"""
        Generate a recipe with the following details:
        - **Tags**: {tags}
        - **Servings**: {servings}
        - **Measurement**: {units}
        - **Additional Instructions**:
        """

        steps = ast.literal_eval(row["steps"])
        ingredients_str = row["ingredients"]
        ingredients = ingredients_str.split(",")
        title = row["title"]
        ingredients_list = "\n".join([f"- {ingredient}" for ingredient in ingredients])
        steps_list = "\n".join([f"- {step}" for step in steps])

        assistant_message = f"""
        ---
        **Title**:
        {title}

        **Tags**:
        {tags}

        **Servings**:
        {servings}

        **Ingredients**:
        {ingredients_list}

        **Steps**:
        {steps_list}

        ---
        """

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message},
        ]

        return messages

    uploaded_df_convo = uploaded_df.apply(create_dynamic_prompt, axis=1).tolist()
    uploaded_df_convo = pd.DataFrame({"conversations": uploaded_df_convo})
    combined_df = pd.concat([dataset_df, uploaded_df_convo])
    dataset = Dataset.from_pandas(combined_df)

    def convert_conversations_format(examples):
        formatted_conversations = []
        for convo in examples["conversations"]:
            if isinstance(convo, str):
                formatted_convo = ast.literal_eval(convo)
            else:
                formatted_convo = convo
            formatted_conversations.append(formatted_convo)
        return {"conversations": formatted_conversations}

    dataset = dataset.map(convert_conversations_format, batched=True)
    dataset = standardize_sharegpt(dataset)

    # Step 4: Train the model
    print("Training model...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer),
        dataset_num_proc=2,
        packing=False,
        args=TrainingArguments(
            per_device_train_batch_size=32,
            gradient_accumulation_steps=8,
            warmup_steps=5,
            num_train_epochs=3,
            learning_rate=2e-4,
            fp16=not is_bfloat16_supported(),
            bf16=is_bfloat16_supported(),
            logging_steps=10,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=3407,
            output_dir=checkpoint_dir,
            save_steps=20,
            save_total_limit=3,
        ),
    )
    vol.commit()  
    trainer = train_on_responses_only(
        trainer,
        instruction_part="<|start_header_id|>user<|end_header_id|>\n\n",
        response_part="<|start_header_id|>assistant<|end_header_id|>\n\n",
    )
    try:
        print("Attempting to resume training from checkpoint...")
        trainer.train(resume_from_checkpoint=True)
    except Exception as e:
        print(f"Failed to resume from checkpoint: {e}. Starting training from scratch.")
        trainer.train()

    # Step 5: Save the model
    print("Saving model...")
    model.save_pretrained_merged(model_save_dir, tokenizer, save_method="merged_16bit")
    model.push_to_hub_merged(
        "esha111/model_whats4dinner_3epochs_simpler",
        tokenizer,
        save_method="merged_16bit",
        token=os.environ["HF_TOKEN"],
    )
    model.push_to_hub_gguf(
        "esha111/model_whats4dinner_3epochs_simpler",
        tokenizer,
        quantization_method=["q4_k_m", "q8_0", "q5_k_m"],
        token=os.environ["HF_TOKEN"],
    )

    print("Fine-tuning complete!")
