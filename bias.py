from transformers import pipeline
import os, requests
from dotenv import load_dotenv

load_dotenv()

#interacts with the model remotely using hf inference api, requires HF_KEY in .env
def get_bias(text):
    url = "https://api-inference.huggingface.co/models/bucketresearch/politicalBiasBERT"
    headers = {"Authorization": f"Bearer {os.getenv('HF_KEY')}"}
    response = requests.post(url, headers=headers, json={"inputs": text})
    # example of result -> [{'label': 'RIGHT', 'score': 0.4443}, {'label': 'LEFT', 'score': 0.3080}, {'label': 'CENTER', 'score': 0.2475}]
    result = response.json()[0]
    prediction = max(result, key=lambda x: x["score"])
    return {
        "text" : text,
        "predicted_label" : prediction["label"],
        "score" : prediction["score"],
        "probabilities" : result
    }

#initialize the Hugging Face inference pipeline
classifier = pipeline("text-classification", model="bucketresearch/politicalBiasBERT")

#interacts with the model locally using pipeline from transformers
def get_bias_local(text):
    result = classifier(text)
    prediction = result[0]
    return {
        "text" : text,
        "predicted_label" : prediction["label"],
        "score" : prediction["score"],
    }

