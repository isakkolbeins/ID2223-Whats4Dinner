import gradio as gr
from huggingface_hub import InferenceClient
import pandas as pd
from datasets import Dataset, load_dataset
import os
import ast


HF_TOKEN_WRITE = os.getenv("HF_TOKEN_WRITE")


######################################################################
#           
#                           Static Inputs 
#           
######################################################################
CSV_DATASET_PATH = "recipes.csv"
HF_DATASET_PATH = "kolbeins/uploaded-recipes"
#client = InferenceClient("kolbeins/model",  token=HF_TOKEN_WRITE) - Basic one from lab2 
#client = InferenceClient("kolbeins/model_whats4dinner",  token=HF_TOKEN_WRITE)
#client = InferenceClient("kolbeins/model_whats4dinner_3epochs",  token=HF_TOKEN_WRITE)
client = InferenceClient("kolbeins/model_whats4dinner_3epochs_simpler",  token=HF_TOKEN_WRITE)

#client = InferenceClient("esha111/recipe-generator",  token=HF_TOKEN_WRITE)

# Options for dietary restrictions and cuisines
dietary_restrictions = [ "Gluten-Free", "Vegan", "Vegetarian", "Dairy-Free", "Nut-Free", "Soy-Free", "Keto", "Paleo", "Low-Carb", "Halal", "Kosher"]
cuisines = [ "American", "Chinese", "French", "Greek", "Indian", "Italian", "Japanese", "Korean", "Mexican", "Middle Eastern", "Spanish", "Thai", "Vietnamese"]
TAG_OPTIONS = dietary_restrictions + cuisines

######################################################################
MAX_NEW_TOKENS = 350    #512
TEMPERATURE = 0.7       #0,7
TOP_P = 0.8            #0,95

SYSTEM_MESSAGE1 = """ You are a recipe generator. Based on the inputs provided, generate a detailed and correctly formatted recipe that meets the user's needs. Follow the instructions carefully. 

**Input format**:
The user will provide the following details:
- **Tags**: One or more dietary restrictions or cuisine types or other relevant tags  (e.g., Vegan, Gluten-Free, Italian, Indian, Mexican etc.)
- **Servings**: A number between 1 and 10 representing the servings (e.g., 4)
- **Measurement**: Either Metric or Imperial, depending on the user's preference (e.g., Metric, Imperial)
- **Additional Instructions**: Any additional information, such as cooking methods or ingredient preferences (optional)

**Output format**:
The recipe should be organized as follows:

---
**Title**: 
- Provide a creative and descriptive title for the recipe. Make it clear what the recipe is (e.g., "Vegan Italian Pasta" or "Gluten-Free Chocolate Cake").

**Tags**: 
- Provide a list of relevant dietary tags (e.g., Vegan, Gluten-Free) and cuisine tags (e.g., Italian, Indian, Mexican). Use commas to separate tags.

**Servings**: 
- The number of servings the recipe will produce

**Ingredients**:
- List all ingredients required to make the recipe, scaled to the number of servings provided. Use the unit of measurement specified (Metric or Imperial).
- Ensure the quantities are accurate for the specified serving size. For example, if the serving size is 4 and the original recipe calls for 1 cup of flour, the output should reflect 4 cups if serving size increases. 
- If the units change (e.g., from Imperial to Metric), make sure to convert the quantities accordingly.

**Steps**:
- List clear, easy-to-follow steps for preparing the dish. Ensure each step is in logical order.
- Include any details from the Additional Instructions (if provided), such as cooking methods or special ingredient preferences.

---
Please ensure to follow the instructions carefully and format the output exactly as specified above.
"""
SYSTEM_MESSAGE2 = "You are a recipe generator. Based on the inputs provided, generate a detailed and correctly formatted recipe that meets the user's needs. Follow the instructions carefully." 


SYSTEM_MESSAGE = SYSTEM_MESSAGE1


######################################################################
#           
#                           LLM Inference
#           
######################################################################

def respond(
    message,
    history: list[tuple[str, str]],
    system_message,
    use_history,
    servings,
    tags,
    units,
    max_tokens,
    temperature,
    top_p
):
    messages = [{"role": "system", "content": system_message }] #SYSTEM_MESSAGE}]

    if use_history == "Yes":
        for val in history:
            if val[0]:
                messages.append({"role": "user", "content": val[0]})
            if val[1]:
                messages.append({"role": "assistant", "content": val[1]})
    
    user_message = f""" 
    Generate a recipe with the following details:
    - **Tags**: {",".join(tags)}
    - **Servings**: {servings}
    - **Measurement**: {units}
    - **Additional Instructions**: {message} 
    """

    messages.append({"role": "user", "content": user_message})

    response = ""

    for message in client.chat_completion(
        messages,
        max_tokens=max_tokens,
        stream=True,
        temperature=temperature,
        top_p=top_p,
    ):
        token = message.choices[0].delta.content

        response += token
       
        # Trimming leading spaces in response (fixing codeblock)
        cleaned_lines = []
        for line in response.splitlines():
            cleaned_lines.append(line.lstrip())  # Remove leading spaces 
        # Join the lines back into a single string
        sanitized_response =  '\n'.join(cleaned_lines)

        yield sanitized_response

    #history.append((message, response))
    history.append((user_message, sanitized_response))


######################################################################
#           
#                           Recipe upload 
#           
######################################################################

def save_recipe(title, serving_size, tags_list, steps_list, ingredients_list):

    steps_str = repr(steps_list)
    ingredients_str = repr(ingredients_list)
    tags_str = repr(tags_list)
    serving_size_int = int(serving_size)

    new_row = {"title": title, "servings": serving_size_int, "tags": tags_str, "steps": steps_str, "ingredients": ingredients_str}


    save_recipe_CSV(new_row)
    save_recipe_HF(new_row)

    # Return message, and clear all [submit_output, title_input, serving_size, tags, steps_list, ingredients_list, steps_text, ingredients_text, step_input, ingredient_input]
    return f"Recipe '{title}' has been added successfully!", "", 4, [], [], [], "", "", "", "",

# Saves the uploaded recipe as a row in a local CVS file
def save_recipe_CSV(new_row):

    if not os.path.exists(CSV_DATASET_PATH):
        with open(CSV_DATASET_PATH, "w") as f:
            pd.DataFrame(columns=["title", "steps", "ingredients"]).to_csv(f, index=False)

    # Get dataframe from CVS
    df = pd.read_csv(CSV_DATASET_PATH)
    # Add the new row
    df = pd.concat([df, pd.DataFrame([new_row])])
    # Set Servings as int before saving CVS
    df["servings"] = df["servings"].astype(int)
    # Save CVS 
    df.to_csv(CSV_DATASET_PATH, index=False)


# Saves the uploaded recipe as a row in Hugging Face dataset
def save_recipe_HF(new_row):
    
    dataset = get_dataset()     # Get dataset from HF
    df = dataset.to_pandas()    # Convert HF dataset to DataFrame
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)    # Add the new recipe
    updated_dataset = Dataset.from_pandas(df) # Convert back to HF Dataset
    # Push the updated dataset to hugging face
    updated_dataset.push_to_hub(HF_DATASET_PATH, token=HF_TOKEN_WRITE)

def get_dataset():
    try:
        # Always use the token for authentication
        print("Attempting to load the dataset from Hugging Face...")
        ds = load_dataset(HF_DATASET_PATH, split="train")
        return ds
    except Exception as e:
        print(f"Error loading dataset: {e}")
        # Initialize an empty DataFrame
        columns = ["title", "steps", "ingredients", "servings", "tags"]
        df = pd.DataFrame(columns=columns)
        return Dataset.from_pandas(df)


######################################################################
#           
#                           Display recipes  
#           
######################################################################

def view_recipes():
    # Check if the dataset exists
    if not os.path.exists(CSV_DATASET_PATH):
        return "No recipes found! Upload some recipes first."

    # Load recipes
    df = pd.read_csv(CSV_DATASET_PATH)
    if df.empty:
        return "No recipes found! Upload some recipes first."
    
    # Reverse the order of recipes
    df = df.iloc[::-1]

    # Generate HTML segments for each recipe
    recipes_html = ""
    for _, row in df.iterrows():
        steps_list = ast.literal_eval(row["Steps"])
        ingredients_list = ast.literal_eval(row["Ingredients"])
        tags_list = ast.literal_eval(row["Tags"])
        
        recipes_html += f"""
        <div style="border: 1px solid #ccc; padding: 10px; margin: 10px; border-radius: 5px;">
            <h3>{row['Title']}</h3>
            <p>{", ".join(tags_list)}</p>         
            <p>{row['Servings']} Servings </p>         
        """
        recipes_html += steps_as_html(steps_list)
        recipes_html += ingredients_as_html(ingredients_list)
        recipes_html += "</div>"

    return recipes_html

######################################################################
#           
#     Interactive UI functions for adding steps and ingredients  
#           
######################################################################

# Adds a step, append to list and html and reset textbox
def add_step(step, steps):
    if step:
        steps.append(step)
    steps_html = steps_as_html(steps)
    return steps, gr.update(value=steps_html), gr.update(value="")

# Returns the steps list as an HTML list, with a title and a border
def steps_as_html(steps_list):
    steps_html = f"""
        <h4>Steps:</h4>
        <div style="border: 1px solid #ccc; padding: 10px; margin: 10px; border-radius: 5px;">    
            <ol>
        """
    for step in steps_list:
        steps_html += f"<li>{step}</li>"

    steps_html += "</ol></div>"
    return steps_html

# Adds an ingredient, append to list and html and reset textbox
def add_ingredient(ingredient, ingredients):
    if ingredient:
        ingredients.append(ingredient)
    ingredients_html = ingredients_as_html(ingredients)
    return ingredients, gr.update(value=ingredients_html), gr.update(value="")

# Returns the ingredients list as an HTML list, with a title and a border
def ingredients_as_html(ingredients_list):
    ingredients_html = f"""
        <h4>Ingredients:</h4>
        <div style="border: 1px solid #ccc; padding: 10px; margin: 10px; border-radius: 5px;">    
            <ul>
        """
    for ingredient in ingredients_list:
            ingredients_html += f"<li>{ingredient}</li>"

    ingredients_html += "</ul></div>"
    return ingredients_html


######################################################################
#           
#                          Gradio UI layout
#           
######################################################################

with gr.Blocks(fill_height=True) as app:
    
    gr.Markdown("## Whats 4 Dinner ")
    gr.Markdown("#### Recipe Generator")

    with gr.Tabs():
       
        # Generation 
        with gr.Tab("Create Recipe"):
            with gr.Row(equal_height=True, min_height=500): 
                with gr.Column():                       
                    with gr.Row(): 
                        serving_size = gr.Slider(minimum=1, maximum=10, value=4, step=1, label="Serving Size")
                        units_of_measure = gr.Radio(["Imperial", "Metric"], value="Imperial", label="Units of measure")
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("Tags")
                            tags = gr.CheckboxGroup(choices=TAG_OPTIONS, show_label=False)
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("Additional instructions, if any:")
                            instructions = gr.Textbox(value="", label="Additional instructions", show_label=True, submit_btn="Generate")
                with gr.Column(): 
                    chatbox = gr.Chatbot(label="Recipe Chatbot", elem_id="chatbot")
            
            with gr.Accordion("Generation settings", open=False):
                with gr.Row(equal_height=True):
                    with gr.Column(): 
                        use_history = gr.Radio(["Yes", "No"], value="No", label="Use chat history")
                        max_new_tokens = gr.Slider(minimum=1, maximum=2048, value=MAX_NEW_TOKENS, step=1, label="Max new tokens")
                        temperature = gr.Slider(minimum=0.1, maximum=2.0, value=TEMPERATURE, step=0.01, label="Temperature")
                        top_p = gr.Slider(minimum=0.1, maximum=0.99, value=TOP_P, step=0.01, label="Top-p (nucleus sampling)")
                    with gr.Column():
                        with gr.Row(equal_height=True):
                            system_message = gr.Textbox(value=SYSTEM_MESSAGE, label="System message", lines=20)


            gr.ChatInterface(
                fn=respond,
                textbox=instructions,
                chatbot=chatbox,
        
                additional_inputs=[
                    system_message,
                    use_history,
                    serving_size,
                    tags,
                    units_of_measure,
                    max_new_tokens,
                    temperature,
                    top_p
                ]
            )            
        
            
        # Upload     
        with gr.Tab("Upload Recipe"):
            
            with gr.Row(equal_height=True):
                with gr.Column(scale=2):
                    title_input = gr.Textbox(label="Recipe Title", placeholder="Enter the title of your recipe")
                with gr.Column(scale=1):
                    serving_size = gr.Slider(minimum=1, maximum=10, value=4, step=1, label="Serving Size")

            with gr.Row():    
                with gr.Column(scale=1):
                    tags = gr.CheckboxGroup(choices=TAG_OPTIONS, label="Tags")

            with gr.Row():
                with gr.Column():
                    steps_list = gr.State([])
                    steps_text = gr.HTML(label="Steps", value= f"<h4>Steps:</h4>" )

            with gr.Row(equal_height=True):
                with gr.Column(scale=9):
                    step_input = gr.Textbox(show_label=False, label="Next step", placeholder="Enter a step")
                with gr.Column(scale=1, min_width=100):
                    add_step_button = gr.Button("Add Step")
                   
                    add_step_button.click(
                        add_step,
                        inputs=[step_input, steps_list],
                        outputs=[steps_list, steps_text, step_input],
                    )


            with gr.Row():
                with gr.Column():
                    # Dynamic fields for ingredients
                    ingredients_list = gr.State([])
                    ingredients_text = gr.HTML(label="Ingredients", value= f"<h4>Ingredients:</h4>")

            with gr.Row(equal_height=True):
                with gr.Column(scale=9):
                    ingredient_input = gr.Textbox(show_label=False, label="Next ingredient", placeholder="Enter an ingredient")
                with gr.Column(scale=1, min_width=100):
                    add_ingredient_button = gr.Button("Add Ingredient")

                    
                    add_ingredient_button.click(
                        add_ingredient,
                        inputs=[ingredient_input, ingredients_list],
                        outputs=[ingredients_list, ingredients_text, ingredient_input],
                    )

            with gr.Row():
                with gr.Column():
                    submit_button = gr.Button("Upload Recipe")
                    submit_output = gr.HTML(label="Status")

                    submit_button.click(
                        save_recipe,
                        inputs=[title_input, serving_size, tags, steps_list, ingredients_list],
                        outputs=[submit_output, title_input, serving_size, tags, steps_list, ingredients_list, steps_text, ingredients_text, step_input, ingredient_input ]
                    )

        # Tab for viewing recipes
        with gr.Tab("View Recipes"):
            view_button = gr.Button("Refresh Recipes")
            recipes_output = gr.HTML(label="Uploaded Recipes")

            view_button.click(
                view_recipes,
                outputs=recipes_output,
            )

if __name__ == "__main__":
    app.launch()
