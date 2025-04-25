# evaluate_sentiment_siebert.py

import pandas as pd
from transformers import pipeline
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt

# =====================
# Load Binary Sentiment Model (Siebert)
# =====================
print("[+] Loading Siebert sentiment model...")
sentiment_pipeline = pipeline(
    "sentiment-analysis", 
    model="siebert/sentiment-roberta-large-english"
)

def get_sentiment(text):
    try:
        result = sentiment_pipeline(text[:512])[0]
        return result["label"].capitalize()  # returns 'POSITIVE' or 'NEGATIVE'
    except:
        return "Negative"  # fallback

# =====================
# Load and Filter Dataset
# =====================
print("[+] Loading dataset...")
df = pd.read_csv("/Users/vibhabhavikatti/Documents/CS273 - NLP/Capstone/news_sentiment_analysis.csv")

# Normalize and drop "Neutral"
df["Sentiment"] = df["Sentiment"].str.capitalize()
df = df[df["Sentiment"].isin(["Positive", "Negative"])]

print(f"[+] Using {len(df)} Positive/Negative samples")

# Optional: sample for speed
# df = df.sample(1000, random_state=42)

# =====================
# Run Predictions
# =====================
print("[+] Predicting sentiments...")
df["predicted"] = df["Description"].apply(get_sentiment)

# =====================
# Evaluation Report
# =====================
print("\n=== Classification Report ===")
print(classification_report(df["Sentiment"], df["predicted"], labels=["Positive", "Negative"]))

# =====================
# Confusion Matrix
# =====================
cm = confusion_matrix(df["Sentiment"], df["predicted"], labels=["Positive", "Negative"])

sns.heatmap(cm, annot=True, fmt='d', cmap="Greens", xticklabels=["Positive", "Negative"], yticklabels=["Positive", "Negative"])
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("Confusion Matrix: Binary Sentiment (Siebert)")
plt.show()
