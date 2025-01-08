import gradio as gr
from huggingface_hub import InferenceClient
import pandas as pd
from datasets import Dataset, load_dataset
import os
import ast

# Clear the dataset
HF_TOKEN_WRITE = ""
HF_DATASET_PATH = "kolbeins/uploaded-recipes"


columns = ["title", "steps", "ingredients", "servings", "tags"]
df = pd.DataFrame(columns=columns)

updated_dataset = Dataset.from_pandas(df) # Convert back to HF Dataset
# Push the updated dataset to hugging face
updated_dataset.push_to_hub(HF_DATASET_PATH, token=HF_TOKEN_WRITE)