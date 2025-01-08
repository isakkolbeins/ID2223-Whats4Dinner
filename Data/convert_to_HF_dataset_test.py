import pandas as pd
import ast
from datasets import Dataset

def create_dynamic_prompt(row):
    # System message (role: system)
    system_message = """
    You are a recipe generator. Based on the inputs provided, generate a detailed and correctly formatted recipe that meets the user's needs. Follow the instructions carefully. 

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

    # User message (role: user)

    # Extracting the inputs from the row (adjust the column names as per your dataset)
    tags_list = ast.literal_eval(row['steps'])

    tags = ",".join(tags_list)
    servings = row['servings'] 
    units = "Imperial" #the training set is all Imperial ? 

    user_message = f"""
    Generate a recipe with the following details:
    - **Tags**: {tags}
    - **Servings**: {servings}
    - **Measurement**: {units}
    - **Additional Instructions**: 
    """

    steps = ast.literal_eval(row['steps'])

#    ingredients = ast.literal_eval(row['ingredients'])
    # is just a string (not python array)
    ingredients_str = row['ingredients']
    ingredients = ingredients_str.split(',')
    title = row['title']
    ingredients_list = "\n".join([f"- {ingredient}" for ingredient in ingredients])
    steps_list = "\n".join([f"- {step}" for step in steps])


    # Assistant message (role: assistant) – dynamically generated recipe output based on input data
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

    # Combine system, user, and assistant messages
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_message},
    ]

    return messages


# Import CSV to DataFrame (adjust file path as necessary)
df = pd.read_csv("./Data/recipes_5k_pruned_with_units.csv")


# Apply the `create_dynamic_prompt` function to each row in the DataFrame
conversations = df.apply(create_dynamic_prompt, axis=1).tolist()


# Convert the list of conversations to a HuggingFace Dataset
dataset = Dataset.from_dict({"conversations": conversations})

print(dataset[0]["conversations"])

dataset.push_to_hub("kolbeins/recipe-training-5k", token="")
