# ID2223 - Final project - Whats4Dinner 
### ID2223 KTH - Group 0  
> Ísak Arnar Kolbeins and Esha Bilal  

## 




## Diagram
![Model diagram](https://github.com/isakkolbeins/ID2223-Whats4Dinner/blob/main/diagram.png?raw=true)




- [The Huggingface space](https://huggingface.co/spaces/kolbeins/whats4dinner)  




## Fine Tuning LLMs 
Training was conducted on Colab over multiple sessions, and Google Drive used to save checkpoints along the way.  
- The LLM used [Llama-3.2 1B](https://huggingface.co/unsloth/Llama-3.2-1B-Instruct)  
- The dataset used [FineTome-100k](https://huggingface.co/datasets/mlabonne/FineTome-100k)

Then the models were saved on Hugging Face.
- [Model 1](https://huggingface.co/kolbeins/model)  
- [Model 2](https://huggingface.co/esha111/id2223_lab2_correct)  

### LLM Interfaces  
The interface uses the [Gradio chatbot demo](https://huggingface.co/spaces/gradio-templates/chatbot) provided on Hugging Face.
Small changes made to toggle enable/disable the use of chat history for the next response.  


## Improving pipeline scalability and model performance 

### Model-centric approach
**Learning Rate**: Too high a value can cause divergence, while too low slows convergence. A balanced rate like 1e-5 or 3e-5 helps achieve stable learning. We had a learning rate of 2e-4 (0.0002), which might have been too high. However, techniques like learning rate scheduling were also used to prevent overshooting the minimum. This might not have done anything because unstable convergence was still observed with loss jumping from between 0.4 to 1.2 throughout fine-tuning. 

**Batch Size**: Smaller batch sizes introduce more stochasticity, helping escape local minima, while larger ones stabilize training and reduce noise. Batch could be increased to boost model performance, however hardware constraints limit this type of tuning. 

**Epochs**: Balancing underfitting (too few epochs) and overfitting (too many epochs) is crucial to maintain performance. However, more epochs would increase the fine-tuning time. 

### Data-centric approach

**Data Diversity**: A diverse dataset helps the model generalize better across different domains and languages.
Domain-Specific Data: For example, if the target use case is healthcare, training on medical conversations improves relevance.
