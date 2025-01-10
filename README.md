# ID2223 - Final project - Whats4Dinner 
### ID2223 KTH - Group 0  
> Ísak Arnar Kolbeins and Esha Bilal  

#### [🧑‍🍳 UI LIVE HERE 🧑‍🍳](https://huggingface.co/spaces/kolbeins/whats4dinner)

## Introduction
Cooking has always been more than just about putting food on the table, it can be described as a form of expression. A way to get creative and explore new flavors and cuisines, however finding the right recipe can be more than challenging. Especially in the world of popup ads and banners.

Therefore we set out to create a fine tuned LLM to generate custom recipes, based on the user input. The user provides some specifications eg. dietary restrictions, type of cuisine and the number of servings. And the model responds with a recipe including step by step instructions and a list of ingredients.


## Tools and Technologies
- **Kaggle** to get the initial recipe training dataset for fine-tuning. 
- **Pandas** and **Numpy** for data pre-processing. 
- **Pytorch** and **Hugging Face Transformers** to load pre-trained LLMs, llama 3 models.
- **Unsloth/Axolotl**, **QLoRA** and **llama.cpp** for simple and resource efficient fine tuning and saving of LLMs.
- **Google Colab** as GPU environment for initial fine-tuning of pre-trained LLM on the recipe training dataset. 
- **Google Drive**, for storing the checkpoints. 
- **Hugging Face Dataset** to store processed and correct format recipe training dataset. 
- **Hugging Face Models/Spaces** and **Gradio** for storing latest fine-tuned models, Inference API and the GUI. 
- **Modal** for re-training pipeline based on weekly trigger that combines new recipes added by user with old recipes in training dataset.


## Diagram
![Model diagram](https://github.com/isakkolbeins/ID2223-Whats4Dinner/blob/main/diagram.png?raw=true)

## Data
The primary data source used in fine-tuning is the [Food.com Recipes and Reviews dataset](https://www.kaggle.com/datasets/irkaal/foodcom-recipes-and-reviews) from Kaggle, containing over 500k recipes from Food.com. This dataset is quite comprehensive and includes detailed information for each recipe. Including the columns relevant to this project; category, keywords, servings, ingredients, ingredient quantities and steps.

## Data pre-processing
- Drop recipes with missing values.  
- To make the recipes dataset much smaller and have higher quality more rows were dropped. Examples of this are the following. Recipes with certain keywords (deserts, drinks and baking recipes) were dropped. All recipes without rating were also dropped. Also, recipes that had lower ratings than 4.5 and had less than or equal to 2 ratings were dropped. 
- To get the raw data in the correct format (Hugging Face conversational format) for fine-tuning, we needed to extract tags, servings, ingredients with quantities/units and steps, which were relevant for the conservation structure in our use case. Tags were created by joining category and keyword columns. The ingredients in the dataset were missing units and the quantities were in a different column. A LLM, gtp-3.5-turbo, was therefore used to fill in this data based on context given in steps.  
- Then, the three parts of a Hugging Face conversational format dataset were made, the system message, user message and assistant messages, which were then saved to the Hugging Face Dataset. (convert_to_HF_dataset_test.py)


## Training pipeline 
Training was conducted on Colab over multiple sessions, and Google Drive used to save checkpoints along the way. 
Building on a [demo file](https://colab.research.google.com/drive/1T5-zKWM_5OD21QHwXHiV9ixTRR7k3iB9?usp=sharing) from [Unsloth](https://github.com/unslothai/unsloth)

The model used was Llama-3.2-1b-instruct, because of its efficiency and strong capabilities to follow instructions. We used LoRA adapters for the fine tuning because of its efficient adaptation, with few parameters. 

We trained a handful of different models where we tweaked a few things, mainly: 
- Epochs trained for (1 and 3)
- Batch sizes (8 , 16, 32) 
- Gradient Accumulation steps ( 8, 16 )
- Variations of the dataset (more general system message) 

Lastly to save the models to Hugging Face, we opted to save it in float16 precision, optimized for storage and inference speed. 


## Re-training pipeline 
The re-training pipeline mirrors the initial training pipeline, with the additional steps of adding the user uploaded recipes to further enhance the model. First the recipes are converted into a Hugging Face dataset following the conversational format. Then we combine it with the original dataset before continuing with the training. The re-training pipeline runs as an app on Modal, and is triggered every 7 days (at 6:58PM).


## User interface 
The user interface builds on the [Gradio chatbot demo](https://huggingface.co/spaces/gradio-templates/chatbot) with several enhancements. Most noteworthy is the option for users to upload recipes to be saved to a Hugging Face dataset and later used for retraining. Another addition is the prompt builder, allowing users to conveniently build the prompt for the recipe generation. As well as offering generation settings where the user can fine tune decoding parameters such as; top_p temperature and max_new_tokens.

- [The Huggingface space](https://huggingface.co/spaces/kolbeins/whats4dinner)  
