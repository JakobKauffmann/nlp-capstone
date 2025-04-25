from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F
import subprocess

# ========== 1. Sentiment Analysis ==========
print("[+] Loading sentiment model...")
sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

def get_sentiment(text):
    result = sentiment_pipeline(text[:512])[0]
    return result["label"], round(result["score"], 4)


# ========== 2. Political Bias Detection ==========
print("[+] Loading political bias model...")
bias_tokenizer = AutoTokenizer.from_pretrained("bucketresearch/politicalBiasBERT")
bias_model = AutoModelForSequenceClassification.from_pretrained("bucketresearch/politicalBiasBERT")

def get_bias(text):
    inputs = bias_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = bias_model(**inputs).logits
        probs = F.softmax(logits, dim=-1)
    labels = ["LEFT", "CENTER", "RIGHT"]
    predicted_label = labels[probs.argmax()]
    return predicted_label, probs[0].tolist()


# ========== 3. Article Summarization via LLaMA (Ollama) ==========
def summarize_article(text):
    prompt = f"Summarize the following article in 3 sentences:\n{text}"
    result = subprocess.run(["ollama", "run", "llama2"], input=prompt, capture_output=True, text=True)
    return result.stdout.strip()


# ========== 4. Test Inputs ==========
if __name__ == "__main__":
    sample_text = """
    President Biden announced a new economic package aimed at reducing inflation and expanding access to education.
    The proposal has sparked a mixed reaction from both parties in Congress, with Democrats largely supporting it and Republicans voicing concerns about increased spending.
    The White House emphasized that this plan would not raise taxes on middle-class Americans.
    """

    print("\n📊 Sentiment Analysis:")
    sentiment_label, sentiment_score = get_sentiment(sample_text)
    print(f"  → {sentiment_label} ({sentiment_score})")

    print("\n🏛️ Political Bias Classification:")
    bias_label, bias_probs = get_bias(sample_text)
    print(f"  → {bias_label}")
    print(f"  → Probabilities: LEFT={bias_probs[0]:.2f}, CENTER={bias_probs[1]:.2f}, RIGHT={bias_probs[2]:.2f}")

    print("\n📝 Article Summary:")
    summary = summarize_article(sample_text)
    print(summary)
