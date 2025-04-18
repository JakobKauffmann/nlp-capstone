from transformers import pipeline
import os, requests
from dotenv import load_dotenv

load_dotenv()

#interacts with the model remotely using hf inference api, requires HF_KEY in .env
def get_sentiment(text):
    url = "https://api-inference.huggingface.co/models/siebert/sentiment-roberta-large-english"
    headers = {"Authorization": f"Bearer {os.getenv('HF_KEY')}"}
    response = requests.post(url, headers=headers, json={"inputs": text})
    result = response.json()[0]
    prediction = max(result, key=lambda x: x["score"])
    return {
        "text": text,
        "predicted_label": prediction["label"],
        "score": prediction["score"],
        "probabilities": result,
    }

sentiment_analysis = pipeline("sentiment-analysis",model="siebert/sentiment-roberta-large-english")

#interacts with the model locally using pipeline from transformers
def get_sentiment_local(text):
    result = sentiment_analysis(text)
    sentiment = result[0]
    return {
        "text" : text,
        "predicted_label" : sentiment["label"],
        "score" : sentiment["score"],
    }