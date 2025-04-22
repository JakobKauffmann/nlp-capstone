# ----------------------------------------------------------------------------
# IMPORTS (requests, os, json, datetime, time, statistics, traceback, random)
# ----------------------------------------------------------------------------
from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime
import time
import statistics
import traceback
# import random # No longer needed for placeholder credibility score
import requests # For Hugging Face API calls

# Import web scraping functions
from web_scraper.main import scrape_article_content, fetch_articles_for_topic

# Import Together AI client and load environment variables
from together import Together
from dotenv import load_dotenv

# ----------------------------------------------------------------------------
# Load Environment Variables & Initialize API Clients
# ----------------------------------------------------------------------------
load_dotenv()

# Together AI Client (Initialize as before)
together_api_key = os.getenv("TOGETHER_API_KEY")
if not together_api_key:
    print("FATAL: TOGETHER_API_KEY not found.")
    exit(1)
try:
    together_client = Together(api_key=together_api_key)
    print("Together AI client initialized successfully.")
except Exception as e:
    print(f"FATAL: Could not initialize Together AI client: {e}")
    exit(1)

# Hugging Face API Key and Headers (Initialize as before)
hf_api_key = os.getenv("HF_API_KEY")
if not hf_api_key:
    print("FATAL: HF_API_KEY not found.")
    exit(1)
hf_headers = {"Authorization": f"Bearer {hf_api_key}"}
print("Hugging Face API Key loaded.")

# Define Model Endpoints and LLM Model (Same as before)
LLM_MODEL = "meta-llama/Llama-3-8b-chat-hf"
HF_SENTIMENT_URL = "https://api-inference.huggingface.co/models/siebert/sentiment-roberta-large-english"
HF_BIAS_URL = "https://api-inference.huggingface.co/models/bucketresearch/politicalBiasBERT"

# ----------------------------------------------------------------------------
# Flask App Initialization
# ----------------------------------------------------------------------------
app = Flask(__name__)

# ----------------------------------------------------------------------------
# HISTORY HANDLING (Unchanged from v5)
# ----------------------------------------------------------------------------
HISTORY_FILE = os.path.join('static', 'data', 'history.json')
# --- load_history function (same as v5) ---
def load_history():
    history_dir = os.path.dirname(HISTORY_FILE)
    if not os.path.exists(history_dir):
        try: os.makedirs(history_dir)
        except OSError as e: print(f"Error creating directory {history_dir}: {e}"); return []
    if not os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f: json.dump([], f)
            return []
        except IOError as e: print(f"Error creating history file {HISTORY_FILE}: {e}"); return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
            if not isinstance(history_data, list): return []
            return history_data
    except Exception as e: print(f"Unexpected error loading history: {e}"); return []

# --- save_to_history function (same as v5) ---
def save_to_history(input_type, input_value, results):
    history = load_history()
    if not isinstance(results, dict): return
    bias_label = results.get('bias', 'N/A')
    sentiment_label = results.get('sentiment', 'N/A')
    bias_value = results.get('bias_value', 0)
    sentiment_value = results.get('sentiment_value', 0)
    if not isinstance(bias_value, (int, float)): bias_value = 0
    if not isinstance(sentiment_value, (int, float)): sentiment_value = 0
    entry = {
        'id': int(time.time() * 1000),
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'input_type': input_type,
        'input_value': (input_value[:100] + '...') if isinstance(input_value, str) and len(input_value) > 100 else input_value,
        'results': {
            'bias': bias_label.capitalize() if isinstance(bias_label, str) else 'N/A',
            'sentiment': sentiment_label.capitalize() if isinstance(sentiment_label, str) else 'N/A',
            'bias_value': int(bias_value), 'sentiment_value': int(sentiment_value)
        }
    }
    history.insert(0, entry)
    max_history = 20
    if len(history) > max_history: history = history[:max_history]
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f: json.dump(history, f, indent=2)
    except Exception as e: print(f"Unexpected error saving history: {e}")

# ----------------------------------------------------------------------------
# API CALL FUNCTIONS (Unchanged from v5)
# ----------------------------------------------------------------------------

def query_hf_api(api_url, text_input):
    """
    Generic function to query the Hugging Face Inference API with retries
    and specific handling for 503 (model loading) errors.
    """
    max_hf_input_chars = 1000 # Limit input size if necessary
    payload = {"inputs": text_input[:max_hf_input_chars]}
    max_retries = 4 # Increase retries slightly
    initial_delay = 5 # Initial delay in seconds
    last_error = "Unknown HF API Error"
    response = None

    for attempt in range(max_retries):
        print(f"Querying {api_url} (Attempt {attempt+1}/{max_retries})...")
        try:
            response = requests.post(api_url, headers=hf_headers, json=payload, timeout=30) # Longer timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json() # Success

        except requests.exceptions.Timeout:
            last_error = f"Timeout connecting to {api_url}"
            print(f"Warning: {last_error}")
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP error {e.response.status_code} from {api_url}: {e.response.reason}"
            print(f"Warning: {last_error}")
            # --- Specific 503 Handling ---
            if response is not None and response.status_code == 503:
                wait_time = initial_delay * (2 ** attempt) # Exponential backoff (5s, 10s, 20s...)
                print(f"   -> Model may be loading. Waiting {wait_time} seconds before retry...")
                if attempt == max_retries - 1:
                    last_error = "Model failed to load or is unavailable after multiple retries."
                    print(f"Error: {last_error}")
                    return {"error": last_error}
                else:
                    time.sleep(wait_time); continue # Wait and retry
            # --- End Specific 503 Handling ---
            else: # For other HTTP errors, stop retries
                 print(f"Error: Non-503 HTTP error encountered. Stopping retries.")
                 return {"error": last_error}

        except requests.exceptions.RequestException as e:
            last_error = f"Request exception connecting to {api_url}: {e}"
            print(f"Warning: {last_error}")
        except Exception as e:
             last_error = f"Unexpected error during HF API request to {api_url}: {e}"
             print(f"Warning: {last_error}")

        # Wait before general retry (if not a 503 and not the last attempt)
        if attempt < max_retries - 1:
             general_wait = 2 * (attempt + 1)
             print(f"   -> Waiting {general_wait} seconds before general retry...")
             time.sleep(general_wait)

    # If loop finishes without returning
    print(f"Error: Max retries ({max_retries}) exceeded for {api_url}.")
    return {"error": last_error}


def get_sentiment_hf(text):
    # --- Same get_sentiment_hf code as in v5 ---
    print("Getting HF Sentiment...")
    result = query_hf_api(HF_SENTIMENT_URL, text)
    if isinstance(result, dict) and "error" in result:
        return {"sentiment_label": "Error", "sentiment_score": 0, "error": result["error"]}
    try:
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list) and result[0]:
            scores = result[0]
            best_prediction = max(scores, key=lambda x: x.get('score', 0))
            return { "sentiment_label": best_prediction.get('label', 'Unknown').capitalize(), "sentiment_score": int(best_prediction.get('score', 0) * 100) }
        else:
             print(f"Unexpected HF Sentiment API response format: {result}")
             return {"sentiment_label": "Error", "sentiment_score": 0, "error": "Unexpected API response format"}
    except Exception as e:
        print(f"Error processing HF Sentiment response: {e}"); traceback.print_exc()
        return {"sentiment_label": "Error", "sentiment_score": 0, "error": f"Processing error: {e}"}

def get_bias_hf(text):
    # --- Same get_bias_hf code as in v5 ---
    print("Getting HF Bias...")
    result = query_hf_api(HF_BIAS_URL, text)
    if isinstance(result, dict) and "error" in result:
        return {"bias_label": "Error", "bias_score": 0, "error": result["error"]}
    try:
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list) and result[0]:
            scores = result[0]
            best_prediction = max(scores, key=lambda x: x.get('score', 0))
            label_raw = best_prediction.get('label', 'Unknown')
            if label_raw.upper() == 'LEFT': bias_label = 'Left'
            elif label_raw.upper() == 'RIGHT': bias_label = 'Right'
            elif label_raw.upper() == 'CENTER': bias_label = 'Center'
            else: bias_label = label_raw.capitalize()
            return { "bias_label": bias_label, "bias_score": int(best_prediction.get('score', 0) * 100) }
        else:
            print(f"Unexpected HF Bias API response format: {result}")
            return {"bias_label": "Error", "bias_score": 0, "error": "Unexpected API response format"}
    except Exception as e:
        print(f"Error processing HF Bias response: {e}"); traceback.print_exc()
        return {"bias_label": "Error", "bias_score": 0, "error": f"Processing error: {e}"}

def get_llm_features(text):
    # --- Same get_llm_features code as in v5 ---
    if not text or not isinstance(text, str): return {"error": "Invalid text provided for LLM analysis."}
    max_input_chars = 8000
    truncated_text = text[:max_input_chars]
    if len(text) > max_input_chars: print(f"Warning: Truncating input text from {len(text)} to {max_input_chars} chars for LLM.")
    prompt = f"""
Analyze the following text. Provide the output STRICTLY in JSON format with the specified keys.
**Text to Analyze:**
--- START TEXT ---
{truncated_text}
--- END TEXT ---
**Requested JSON Output Structure:**
{{
  "summary": "...", "key_findings": ["...", "..."], "bias_indicators_llm": ["...", "..."],
  "credibility_assessment": "...", "recommended_searches": ["...", "..."]
}}
**Instructions:** Adhere strictly to JSON. Populate all fields (use "N/A" or [] if needed). Summary neutral (3-5 sentences). Bias indicators are phrases suggesting potential bias. Credibility is a brief assessment. Searches are related terms.
Provide ONLY the JSON output, no explanations.
"""
    analysis_result = {"error": "LLM analysis failed."}
    try:
        print(f"Sending request to LLM: {LLM_MODEL} for generative features...")
        start_llm_time = time.time()
        response = together_client.chat.completions.create(
            model=LLM_MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=1024,
        )
        llm_duration = time.time() - start_llm_time
        print(f"LLM response received in {llm_duration:.2f} seconds.")
        raw_response = response.choices[0].message.content
        json_start = raw_response.find('{'); json_end = raw_response.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_string = raw_response[json_start:json_end]
            try:
                parsed_json = json.loads(json_string)
                required_keys = ["summary", "key_findings", "credibility_assessment"]
                if all(key in parsed_json for key in required_keys):
                    analysis_result = parsed_json; print("Successfully parsed JSON response from LLM.")
                else: analysis_result = {"error": "LLM response missing required fields.", "raw_response": raw_response}
            except json.JSONDecodeError as e: analysis_result = {"error": f"Invalid JSON received from LLM: {e}", "raw_response": raw_response}
        else: analysis_result = {"error": "No valid JSON object found in LLM response.", "raw_response": raw_response}
    except Exception as e: print(f"Error during Together AI API call: {e}"); analysis_result = {"error": f"API communication error: {e}"}
    return analysis_result

# ----------------------------------------------------------------------------
# CORE ANALYSIS PIPELINE FUNCTION
# ----------------------------------------------------------------------------
def perform_analysis(input_type, input_value):
    """
    Performs analysis using web scraping, HF API (Bias/Sentiment), and Together AI (LLM features).
    Handles text, URL, and topic inputs, including aggregation.
    """
    start_time = time.time()
    final_results = {}
    articles_analyzed = []
    try:
        # 1. Get Text Content(s) (Same as v5)
        texts_to_analyze = []
        if input_type == 'text': # ... (logic unchanged)
            texts_to_analyze.append({'text': input_value, 'source_url': 'Direct Text Input'})
            final_results['source_display'] = "Direct Text Input"
        elif input_type == 'url': # ... (logic unchanged)
            print(f"Scraping URL: {input_value}")
            article_text = scrape_article_content(input_value)
            if not isinstance(article_text, str) or "error" in article_text.lower() or "no extractable" in article_text.lower():
                 raise ValueError(f"Scraping failed: {article_text if isinstance(article_text, str) else 'Unknown scraping error'}")
            texts_to_analyze.append({'text': article_text, 'source_url': input_value})
            final_results['source_display'] = input_value
        elif input_type == 'topic': # ... (logic unchanged)
            print(f"Fetching articles for topic: {input_value}")
            fetched_articles = fetch_articles_for_topic(input_value, max_articles=3)
            if not fetched_articles: raise ValueError(f"Could not find articles for topic: {input_value}")
            valid_articles_count = 0
            for article in fetched_articles:
                content = article.get('content'); url = article.get('url', 'Unknown URL')
                if content and isinstance(content, str) and "error" not in content.lower() and "no extractable" not in content.lower():
                    texts_to_analyze.append({'text': content, 'source_url': url}); valid_articles_count += 1
                else: print(f"   -> Skipping article {url} due to scraping/content issue.")
            if not texts_to_analyze: raise ValueError(f"Could not successfully get content for any articles for topic: {input_value}")
            final_results['source_display'] = f"Topic: {input_value} ({len(texts_to_analyze)} articles processed)"
        else: raise ValueError(f"Invalid input_type: {input_type}")

        # 2. Analyze each text block (Same as v5)
        for i, item in enumerate(texts_to_analyze): # ... (logic unchanged)
            print(f"--- Analyzing article {i+1} from: {item['source_url']} ---")
            text = item['text']; combined_analysis = {'source_url': item['source_url']}
            sentiment_res = get_sentiment_hf(text); bias_res = get_bias_hf(text)
            if "error" in sentiment_res: print(f"   -> Sentiment analysis warning/error: {sentiment_res['error']}")
            if "error" in bias_res: print(f"   -> Bias analysis warning/error: {bias_res['error']}")
            combined_analysis.update(sentiment_res); combined_analysis.update(bias_res)
            llm_res = get_llm_features(text)
            if "error" in llm_res:
                print(f"   -> LLM analysis warning/error: {llm_res['error']}")
                llm_defaults = { "summary": "N/A", "key_findings": [], "bias_indicators_llm": [], "credibility_assessment": "N/A", "recommended_searches": [] }
                combined_analysis.update(llm_defaults); combined_analysis["llm_error"] = llm_res["error"]
            else: combined_analysis.update(llm_res)
            articles_analyzed.append(combined_analysis)


        # 3. Aggregate and Format Results for Frontend
        if not articles_analyzed: raise ValueError("No analysis results were generated.")
        formatted_results = { 'analysis': {}, 'visualization_data': {}, 'source_display': final_results.get('source_display', 'N/A') }

        # --- Aggregation Logic (Same as v5) ---
        if len(articles_analyzed) == 1: # ... (logic unchanged)
            analysis_data = articles_analyzed[0]; formatted_results['analysis'] = analysis_data
            formatted_results['sentiment'] = analysis_data.get('sentiment_label', 'N/A'); formatted_results['bias'] = analysis_data.get('bias_label', 'N/A')
            formatted_results['summary'] = analysis_data.get('summary', 'N/A'); formatted_results['sentiment_value'] = analysis_data.get('sentiment_score', 0)
            formatted_results['bias_value'] = analysis_data.get('bias_score', 0)
            sentiment_dist = {analysis_data.get('sentiment_label', 'N/A'): analysis_data.get('sentiment_score', 100)}
            bias_dist = {analysis_data.get('bias_label', 'N/A'): analysis_data.get('bias_score', 100)}
            for s_label in ['Positive', 'Negative', 'Neutral']:
                 if s_label not in sentiment_dist: sentiment_dist[s_label] = 0
            for b_label in ['Left', 'Center', 'Right']:
                 if b_label not in bias_dist: bias_dist[b_label] = 0
        else: # ... (logic unchanged)
            valid_articles = [a for a in articles_analyzed if 'error' not in a.get('sentiment_label', 'Error').lower() and 'error' not in a.get('bias_label', 'Error').lower()]
            if not valid_articles:
                 print("Warning: All articles for topic analysis had errors in bias/sentiment."); analysis_data = articles_analyzed[0] # Fallback
                 formatted_results['analysis'] = analysis_data; formatted_results['sentiment'] = analysis_data.get('sentiment_label', 'Error'); formatted_results['bias'] = analysis_data.get('bias_label', 'Error')
                 formatted_results['summary'] = analysis_data.get('summary', 'N/A'); formatted_results['sentiment_value'] = analysis_data.get('sentiment_score', 0); formatted_results['bias_value'] = analysis_data.get('bias_score', 0)
                 sentiment_dist = {formatted_results['sentiment']: formatted_results['sentiment_value']}; bias_dist = {formatted_results['bias']: formatted_results['bias_value']}
            else:
                avg_sentiment_score = statistics.mean([a.get('sentiment_score', 0) for a in valid_articles]) if valid_articles else 0
                avg_bias_score = statistics.mean([a.get('bias_score', 0) for a in valid_articles]) if valid_articles else 0
                sentiment_labels = [a.get('sentiment_label', 'N/A') for a in valid_articles]; bias_labels = [a.get('bias_label', 'N/A') for a in valid_articles]
                overall_sentiment = statistics.mode(sentiment_labels) if sentiment_labels else 'N/A'; overall_bias = statistics.mode(bias_labels) if bias_labels else 'N/A'
                combined_summary = "\n\n---\n\n".join([f"Article {i+1} ({a.get('source_url', '')}):\n{a.get('summary', 'N/A')}" for i, a in enumerate(articles_analyzed)])
                combined_findings = [f"[{a.get('bias_label', '?')}/{a.get('sentiment_label', '?')}] {finding}" for a in articles_analyzed for finding in a.get('key_findings', [])]
                combined_indicators = [f"[{a.get('bias_label', '?')}] {indicator}" for a in articles_analyzed for indicator in a.get('bias_indicators_llm', [])]
                overall_credibility = articles_analyzed[0].get('credibility_assessment', 'N/A')
                combined_searches = list(set(s for a in articles_analyzed for s in a.get('recommended_searches', [])))
                formatted_results['analysis'] = {
                    'sentiment': overall_sentiment, 'sentiment_score': int(avg_sentiment_score), 'political_bias': overall_bias, 'political_bias_score': int(avg_bias_score),
                    'summary': combined_summary, 'key_findings': combined_findings[:10], 'bias_indicators': combined_indicators[:10],
                    'credibility_assessment': overall_credibility, 'recommended_searches': combined_searches[:5] }
                formatted_results['sentiment'] = overall_sentiment; formatted_results['bias'] = overall_bias; formatted_results['summary'] = combined_summary
                formatted_results['sentiment_value'] = int(avg_sentiment_score); formatted_results['bias_value'] = int(avg_bias_score)
                sentiment_dist = {}; bias_dist = {}
                for label in ['Positive', 'Negative', 'Neutral']: scores = [a.get('sentiment_score', 0) for a in valid_articles if a.get('sentiment_label') == label]; sentiment_dist[label] = int(statistics.mean(scores)) if scores else 0
                for label in ['Left', 'Center', 'Right']: scores = [a.get('bias_score', 0) for a in valid_articles if a.get('bias_label') == label]; bias_dist[label] = int(statistics.mean(scores)) if scores else 0

        # --- Final Formatting ---
        formatted_results['visualization_data'] = { 'sentiment_distribution': sentiment_dist, 'bias_distribution': bias_dist }
        # REMOVED placeholder credibility_value generation
        # formatted_results['credibility_value'] = random.randint(30, 75)
        formatted_results['sentiment_value'] = max(0, min(100, formatted_results.get('sentiment_value', 0)))
        formatted_results['bias_value'] = max(0, min(100, formatted_results.get('bias_value', 0)))
        if 'analysis' in formatted_results and 'bias_indicators_llm' in formatted_results['analysis']:
             formatted_results['analysis']['bias_indicators'] = formatted_results['analysis'].pop('bias_indicators_llm')

        print(f"Analysis pipeline completed in {time.time() - start_time:.2f} seconds.")
        return formatted_results

    except ValueError as ve: print(f"ValueError during analysis pipeline: {ve}"); return {"error": f"{ve}"}
    except Exception as e: print(f"Unexpected error during analysis pipeline: {e}"); traceback.print_exc(); return {"error": f"An unexpected analysis error occurred: {getattr(e, 'message', str(e))}"}

# ----------------------------------------------------------------------------
# FLASK ROUTES (Unchanged)
# ----------------------------------------------------------------------------
@app.route('/')
def index():
    history = load_history()
    return render_template('index.html', history=history)

@app.route('/analyze', methods=['POST'])
def analyze_route():
    if not request.is_json: return jsonify({"error": "Request must be JSON"}), 415
    data = request.json; input_type = data.get('input_type'); input_value = data.get('input_value')
    if not input_type or input_type not in ['text', 'url', 'topic']: return jsonify({"error": "Invalid input_type specified"}), 400
    if not input_value or not isinstance(input_value, str) or not input_value.strip(): return jsonify({"error": "Input value cannot be empty"}), 400
    results = perform_analysis(input_type, input_value.strip())
    if "error" in results:
         # Log raw LLM response if available and nested in analysis dict
         if isinstance(results.get('analysis'), dict) and "raw_response" in results['analysis']:
             print(f"LLM Raw Response leading to error:\n{results['analysis']['raw_response']}")
         # Also check if error came directly from HF API calls before LLM
         elif "raw_response" not in results.get('analysis', {}) and results.get("error"):
             print(f"Analysis pipeline error (potentially before LLM): {results.get('error')}")

         return jsonify({"error": results["error"]}), 500 # Return specific error message
    save_to_history(input_type, input_value.strip(), results)
    return jsonify(results)

# ----------------------------------------------------------------------------
# MAIN EXECUTION
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) # Set debug=False for production
