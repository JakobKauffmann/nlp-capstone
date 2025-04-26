# Updated evaluate_sentiment_siebert.py to include Neutral in the report

import pandas as pd
from transformers import pipeline
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt

# =====================
# Load Multi-class Sentiment Model (Cardiff)
# =====================
print("[+] Loading Cardiff sentiment model...")
sentiment_pipeline = pipeline(
    "sentiment-analysis", 
    model="cardiffnlp/twitter-roberta-base-sentiment"
)

# Map model labels to human-readable
label_map = {
    "LABEL_0": "Negative",
    "LABEL_1": "Neutral",
    "LABEL_2": "Positive"
}

def get_sentiment(text):
    try:
        result = sentiment_pipeline(text[:512])[0]
        return label_map[result["label"]]
    except:
        return "Neutral"  # fallback to neutral

# =====================
# Load and Keep All Classes
# =====================
print("[+] Loading dataset...")
df = pd.read_csv("/Users/vibhabhavikatti/Documents/NLP/Capstone/news_sentiment_analysis.csv")

# Capitalize labels
df["Sentiment"] = df["Sentiment"].str.capitalize()

# Keep all three classes
print(f"[+] Using {len(df)} samples across classes: {df['Sentiment'].value_counts().to_dict()}")

# =====================
# Run Predictions
# =====================
print("[+] Predicting sentiments...")
df["predicted"] = df["Description"].apply(get_sentiment)

# =====================
# Evaluation Report (include Neutral)
# =====================
print("\n=== Classification Report ===")
print(classification_report(
    df["Sentiment"], 
    df["predicted"], 
    labels=["Positive", "Neutral", "Negative"]
))

# =====================
# Confusion Matrix (3x3)
# =====================
cm = confusion_matrix(
    df["Sentiment"], 
    df["predicted"], 
    labels=["Positive", "Neutral", "Negative"]
)

sns.heatmap(cm, annot=True, fmt='d', cmap="Blues", 
            xticklabels=["Positive", "Neutral", "Negative"], 
            yticklabels=["Positive", "Neutral", "Negative"])
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("Confusion Matrix: Sentiment (3-class)")
plt.show()
