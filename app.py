# ----------------------------------------------------------------------------
# IMPORTS (requests, os, json, datetime, time, statistics, traceback, re)
# ----------------------------------------------------------------------------
from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime
import time
import statistics
import traceback
import re # For keyword matching in credibility mapping
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
together_api_key = os.getenv("TOGETHER_API_KEY")
hf_api_key = os.getenv("HF_API_KEY")

if not together_api_key or not hf_api_key:
    print("FATAL: API Keys (TOGETHER_API_KEY, HF_API_KEY) not found.")
    exit(1)
try:
    together_client = Together(api_key=together_api_key)
    print("Together AI client initialized successfully.")
except Exception as e:
    print(f"FATAL: Could not initialize Together AI client: {e}")
    exit(1)
hf_headers = {"Authorization": f"Bearer {hf_api_key}"}
print("Hugging Face API Key loaded.")

LLM_MODEL = "meta-llama/Llama-3-8b-chat-hf"
HF_SENTIMENT_URL = "https://api-inference.huggingface.co/models/siebert/sentiment-roberta-large-english"
HF_BIAS_URL = "https://api-inference.huggingface.co/models/bucketresearch/politicalBiasBERT"

# ----------------------------------------------------------------------------
# Flask App Initialization
# ----------------------------------------------------------------------------
app = Flask(__name__)

# ----------------------------------------------------------------------------
# HISTORY HANDLING (Added functions to modify history)
# ----------------------------------------------------------------------------
HISTORY_FILE = os.path.join('static', 'data', 'history.json')

def load_history():
    """Load analysis history from JSON file. Create it if it doesn't exist."""
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
            # Ensure data is a list and items have 'id'
            if not isinstance(history_data, list):
                print(f"Warning: History file {HISTORY_FILE} is not a valid JSON list. Resetting.")
                return []
            # Ensure IDs are integers if they exist
            for item in history_data:
                if 'id' in item:
                    try:
                        item['id'] = int(item['id'])
                    except (ValueError, TypeError):
                        print(f"Warning: Invalid ID found in history item: {item}. Skipping ID conversion.")

            return history_data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {HISTORY_FILE}: {e}. Resetting history.")
        return []
    except Exception as e:
        print(f"Unexpected error loading history: {e}")
        traceback.print_exc()
        return []

def save_history_file(history_data):
    """Saves the provided history data list to the JSON file."""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2)
        return True
    except IOError as e:
        print(f"Error writing history file {HISTORY_FILE}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error saving history: {e}")
        traceback.print_exc()
        return False

def add_to_history(input_type, input_value, results):
    """Adds a new analysis result to the history."""
    history = load_history()
    if not isinstance(results, dict): return

    bias_label = results.get('bias', 'N/A')
    sentiment_label = results.get('sentiment', 'N/A')
    bias_value = results.get('bias_value', 0)
    sentiment_value = results.get('sentiment_value', 0)
    if not isinstance(bias_value, (int, float)): bias_value = 0
    if not isinstance(sentiment_value, (int, float)): sentiment_value = 0

    # Generate a unique ID (using timestamp is generally safe enough for this scale)
    new_id = int(time.time() * 1000)

    entry = {
        'id': new_id, # Use generated ID
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

    save_history_file(history) # Use the dedicated save function

# ----------------------------------------------------------------------------
# API CALL FUNCTIONS (Unchanged)
# ----------------------------------------------------------------------------
def query_hf_api(api_url, text_input):
    max_hf_input_chars = 1000; payload = {"inputs": text_input[:max_hf_input_chars]}; max_retries = 4; initial_delay = 5
    last_error = "Unknown HF API Error"; response = None
    for attempt in range(max_retries):
        print(f"Querying {api_url} (Attempt {attempt+1}/{max_retries})...")
        try:
            response = requests.post(api_url, headers=hf_headers, json=payload, timeout=30)
            response.raise_for_status(); return response.json()
        except requests.exceptions.Timeout: last_error = f"Timeout connecting to {api_url}"; print(f"Warning: {last_error}")
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP error {e.response.status_code} from {api_url}: {e.response.reason}"; print(f"Warning: {last_error}")
            if response is not None and response.status_code == 503:
                wait_time = initial_delay * (2 ** attempt); print(f"   -> Model may be loading. Waiting {wait_time} seconds before retry...")
                if attempt == max_retries - 1: last_error = "Model failed to load or is unavailable after multiple retries."; print(f"Error: {last_error}"); return {"error": last_error}
                else: time.sleep(wait_time); continue
            else: print(f"Error: Non-503 HTTP error encountered. Stopping retries."); return {"error": last_error}
        except requests.exceptions.RequestException as e: last_error = f"Request exception connecting to {api_url}: {e}"; print(f"Warning: {last_error}")
        except Exception as e: last_error = f"Unexpected error during HF API request to {api_url}: {e}"; print(f"Warning: {last_error}")
        if attempt < max_retries - 1: general_wait = 2 * (attempt + 1); print(f"   -> Waiting {general_wait} seconds before general retry..."); time.sleep(general_wait)
    print(f"Error: Max retries ({max_retries}) exceeded for {api_url}.")
    return {"error": last_error}

def get_sentiment_hf(text):
    print("Getting HF Sentiment (Binary)...")
    result = query_hf_api(HF_SENTIMENT_URL, text)
    if isinstance(result, dict) and "error" in result: return {"sentiment_binary": None, "error": result["error"]}
    try:
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list) and result[0]:
            scores = result[0]; best_prediction = max(scores, key=lambda x: x.get('score', 0))
            label = best_prediction.get('label', 'Unknown').upper()
            sentiment_binary = 1 if label == 'POSITIVE' else 0
            return {"sentiment_binary": sentiment_binary}
        else: print(f"Unexpected HF Sentiment API response format: {result}"); return {"sentiment_binary": None, "error": "Unexpected API response format"}
    except Exception as e: print(f"Error processing HF Sentiment response: {e}"); traceback.print_exc(); return {"sentiment_binary": None, "error": f"Processing error: {e}"}

def get_bias_hf(text):
    print("Getting HF Bias...")
    result = query_hf_api(HF_BIAS_URL, text)
    if isinstance(result, dict) and "error" in result: return {"bias_label": "Error", "bias_score": 0, "error": result["error"]}
    try:
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list) and result[0]:
            scores = result[0]; best_prediction = max(scores, key=lambda x: x.get('score', 0))
            label_raw = best_prediction.get('label', 'Unknown')
            if label_raw.upper() == 'LEFT': bias_label = 'Left'
            elif label_raw.upper() == 'RIGHT': bias_label = 'Right'
            elif label_raw.upper() == 'CENTER': bias_label = 'Center'
            else: bias_label = label_raw.capitalize()
            return { "bias_label": bias_label, "bias_score": int(best_prediction.get('score', 0) * 100) }
        else: print(f"Unexpected HF Bias API response format: {result}"); return {"bias_label": "Error", "bias_score": 0, "error": "Unexpected API response format"}
    except Exception as e: print(f"Error processing HF Bias response: {e}"); traceback.print_exc(); return {"bias_label": "Error", "bias_score": 0, "error": f"Processing error: {e}"}

def get_llm_features(text):
    if not text or not isinstance(text, str): return {"error": "Invalid text provided for LLM analysis."}
    max_input_chars = 8000; truncated_text = text[:max_input_chars]
    if len(text) > max_input_chars: print(f"Warning: Truncating input text from {len(text)} to {max_input_chars} chars for LLM.")
    prompt = f"""Analyze the following text and provide the output STRICTLY in JSON format:
{{
  "summary": "...", "key_findings": ["...", "..."], "bias_indicators_llm": ["...", "..."],
  "credibility_assessment": "...", "recommended_searches": ["...", "..."]
}}
Instructions: Adhere strictly to JSON. Populate all fields (use "N/A" or [] if needed). Summary neutral (3-5 sentences). Bias indicators are phrases suggesting potential bias. Credibility is a brief assessment. Searches are related terms. Provide ONLY JSON.
Text:
{truncated_text}"""
    analysis_result = {"error": "LLM analysis failed."}
    try:
        print(f"Sending request to LLM: {LLM_MODEL} for generative features...")
        start_llm_time = time.time()
        response = together_client.chat.completions.create( model=LLM_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=1024, )
        llm_duration = time.time() - start_llm_time; print(f"LLM response received in {llm_duration:.2f} seconds.")
        raw_response = response.choices[0].message.content
        json_start = raw_response.find('{'); json_end = raw_response.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_string = raw_response[json_start:json_end]
            try:
                parsed_json = json.loads(json_string)
                required_keys = ["summary", "key_findings", "credibility_assessment"]
                if all(key in parsed_json for key in required_keys): analysis_result = parsed_json; print("Successfully parsed JSON response from LLM.")
                else: analysis_result = {"error": "LLM response missing required fields.", "raw_response": raw_response}
            except json.JSONDecodeError as e: analysis_result = {"error": f"Invalid JSON received from LLM: {e}", "raw_response": raw_response}
        else: analysis_result = {"error": "No valid JSON object found in LLM response.", "raw_response": raw_response}
    except Exception as e: print(f"Error during Together AI API call: {e}"); analysis_result = {"error": f"API communication error: {e}"}
    return analysis_result

# ----------------------------------------------------------------------------
# HELPER FUNCTION: Map Credibility Text to Level (Unchanged)
# ----------------------------------------------------------------------------
def map_credibility_to_level(assessment_text):
    if not assessment_text or not isinstance(assessment_text, str): return "Medium"
    text_lower = assessment_text.lower()
    high_keywords = ["credible", "sourced", "factual", "objective", "verified", "well-supported", "neutral tone"]
    low_keywords = ["lacks sourcing", "unsourced", "no source", "emotionally charged", "opinion piece", "biased language", "unverified", "misleading", "propaganda"]
    medium_keywords = ["balanced", "multiple viewpoints", "some sources", "unclear", "subjective", "potential bias"]
    if any(keyword in text_lower for keyword in low_keywords): return "Low"
    if any(keyword in text_lower for keyword in high_keywords): return "High"
    if any(keyword in text_lower for keyword in medium_keywords): return "Medium"
    return "Medium"

# ----------------------------------------------------------------------------
# CORE ANALYSIS PIPELINE FUNCTION (Unchanged)
# ----------------------------------------------------------------------------
def perform_analysis(input_type, input_value):
    start_time = time.time(); final_results = {}; articles_analyzed = []
    try:
        texts_to_analyze = []
        if input_type == 'text': texts_to_analyze.append({'text': input_value, 'source_url': 'Direct Text Input'}); final_results['source_display'] = "Direct Text Input"
        elif input_type == 'url':
            print(f"Scraping URL: {input_value}"); article_text = scrape_article_content(input_value)
            if not isinstance(article_text, str) or "error" in article_text.lower() or "no extractable" in article_text.lower(): raise ValueError(f"Scraping failed: {article_text if isinstance(article_text, str) else 'Unknown error'}")
            texts_to_analyze.append({'text': article_text, 'source_url': input_value}); final_results['source_display'] = input_value
        elif input_type == 'topic':
            print(f"Fetching articles for topic: {input_value}"); fetched_articles = fetch_articles_for_topic(input_value, max_articles=3)
            if not fetched_articles: raise ValueError(f"Could not find articles for topic: {input_value}")
            for article in fetched_articles:
                content = article.get('content'); url = article.get('url', 'Unknown URL')
                if content and isinstance(content, str) and "error" not in content.lower() and "no extractable" not in content.lower(): texts_to_analyze.append({'text': content, 'source_url': url})
                else: print(f"   -> Skipping article {url} due to scraping/content issue.")
            if not texts_to_analyze: raise ValueError(f"Could not get content for any articles for topic: {input_value}")
            final_results['source_display'] = f"Topic: {input_value} ({len(texts_to_analyze)} articles processed)"
        else: raise ValueError(f"Invalid input_type: {input_type}")

        for i, item in enumerate(texts_to_analyze):
            print(f"--- Analyzing article {i+1} from: {item['source_url']} ---"); text = item['text']
            combined_analysis = {'source_url': item['source_url']}
            sentiment_res = get_sentiment_hf(text); bias_res = get_bias_hf(text)
            if "error" in sentiment_res: print(f"   -> Sentiment warning/error: {sentiment_res['error']}")
            if "error" in bias_res: print(f"   -> Bias warning/error: {bias_res['error']}")
            combined_analysis.update(sentiment_res); combined_analysis.update(bias_res)
            llm_res = get_llm_features(text)
            if "error" in llm_res:
                print(f"   -> LLM warning/error: {llm_res['error']}")
                llm_defaults = { "summary": "N/A", "key_findings": [], "bias_indicators_llm": [], "credibility_assessment": "N/A", "recommended_searches": [] }
                combined_analysis.update(llm_defaults); combined_analysis["llm_error"] = llm_res["error"]
            else: combined_analysis.update(llm_res)
            articles_analyzed.append(combined_analysis)

        if not articles_analyzed: raise ValueError("No analysis results were generated.")
        formatted_results = { 'analysis': {}, 'visualization_data': {}, 'source_display': final_results.get('source_display', 'N/A') }

        if len(articles_analyzed) == 1:
            analysis_data = articles_analyzed[0]; formatted_results['analysis'] = analysis_data
            sentiment_binary = analysis_data.get('sentiment_binary')
            formatted_results['sentiment'] = "Positive" if sentiment_binary == 1 else "Negative" if sentiment_binary == 0 else "Error"
            formatted_results['sentiment_value'] = 100 if sentiment_binary == 1 else 0
            formatted_results['bias'] = analysis_data.get('bias_label', 'N/A'); formatted_results['bias_value'] = analysis_data.get('bias_score', 0)
            formatted_results['summary'] = analysis_data.get('summary', 'N/A')
            formatted_results['analysis']['credibility_level'] = map_credibility_to_level(analysis_data.get('credibility_assessment'))
            sentiment_dist = {"Positive": 100 if sentiment_binary == 1 else 0, "Negative": 100 if sentiment_binary == 0 else 0, "Neutral": 0}
            bias_dist = {analysis_data.get('bias_label', 'N/A'): analysis_data.get('bias_score', 100)};
            for b_label in ['Left', 'Center', 'Right']:
                 if b_label not in bias_dist: bias_dist[b_label] = 0
        else:
            valid_articles = [a for a in articles_analyzed if a.get('sentiment_binary') is not None and 'error' not in a.get('bias_label', 'Error').lower()]
            if not valid_articles:
                 print("Warning: All articles for topic analysis had errors."); analysis_data = articles_analyzed[0] # Fallback
                 formatted_results['analysis'] = analysis_data; formatted_results['sentiment'] = "Error"; formatted_results['bias'] = analysis_data.get('bias_label', 'Error')
                 formatted_results['summary'] = analysis_data.get('summary', 'N/A'); formatted_results['sentiment_value'] = 0; formatted_results['bias_value'] = analysis_data.get('bias_score', 0)
                 formatted_results['analysis']['credibility_level'] = map_credibility_to_level(analysis_data.get('credibility_assessment'))
                 sentiment_dist = {"Positive": 0, "Negative": 0, "Neutral": 0}; bias_dist = {formatted_results['bias']: formatted_results['bias_value']}
            else:
                avg_sentiment_binary = statistics.mean([a.get('sentiment_binary', 0) for a in valid_articles])
                overall_sentiment_label = "Positive" if avg_sentiment_binary >= 0.5 else "Negative"; overall_sentiment_value = 100 if overall_sentiment_label == "Positive" else 0
                avg_bias_score = statistics.mean([a.get('bias_score', 0) for a in valid_articles]) if valid_articles else 0
                bias_labels = [a.get('bias_label', 'N/A') for a in valid_articles]; overall_bias = statistics.mode(bias_labels) if bias_labels else 'N/A'
                combined_summary = "\n\n---\n\n".join([f"Article {i+1} ({a.get('source_url', '')}):\n{a.get('summary', 'N/A')}" for i, a in enumerate(articles_analyzed)])
                combined_findings = [f"[{a.get('bias_label', '?')}/{('Pos' if a.get('sentiment_binary')==1 else 'Neg' if a.get('sentiment_binary')==0 else '?')}] {finding}" for a in articles_analyzed for finding in a.get('key_findings', [])]
                combined_indicators = [f"[{a.get('bias_label', '?')}] {indicator}" for a in articles_analyzed for indicator in a.get('bias_indicators_llm', [])]
                credibility_levels = [map_credibility_to_level(a.get('credibility_assessment')) for a in articles_analyzed]; overall_credibility_level = statistics.mode(credibility_levels) if credibility_levels else "Medium"
                overall_credibility_text = articles_analyzed[0].get('credibility_assessment', 'N/A')
                combined_searches = list(set(s for a in articles_analyzed for s in a.get('recommended_searches', [])))
                formatted_results['analysis'] = {
                    'sentiment': overall_sentiment_label, 'sentiment_score': overall_sentiment_value, 'political_bias': overall_bias, 'political_bias_score': int(avg_bias_score),
                    'summary': combined_summary, 'key_findings': combined_findings[:10], 'bias_indicators': combined_indicators[:10],
                    'credibility_assessment': overall_credibility_text, 'credibility_level': overall_credibility_level,
                    'recommended_searches': combined_searches[:5] }
                formatted_results['sentiment'] = overall_sentiment_label; formatted_results['bias'] = overall_bias; formatted_results['summary'] = combined_summary
                formatted_results['sentiment_value'] = overall_sentiment_value; formatted_results['bias_value'] = int(avg_bias_score)
                pos_count = sum(1 for a in valid_articles if a.get('sentiment_binary') == 1); neg_count = len(valid_articles) - pos_count; total_valid = len(valid_articles)
                sentiment_dist = {"Positive": int((pos_count / total_valid) * 100) if total_valid else 0, "Negative": int((neg_count / total_valid) * 100) if total_valid else 0, "Neutral": 0 }
                bias_dist = {};
                for label in ['Left', 'Center', 'Right']: scores = [a.get('bias_score', 0) for a in valid_articles if a.get('bias_label') == label]; bias_dist[label] = int(statistics.mean(scores)) if scores else 0

        formatted_results['visualization_data'] = { 'sentiment_distribution': sentiment_dist, 'bias_distribution': bias_dist }
        formatted_results['sentiment_value'] = max(0, min(100, formatted_results.get('sentiment_value', 0)))
        formatted_results['bias_value'] = max(0, min(100, formatted_results.get('bias_value', 0)))
        if 'analysis' in formatted_results and 'bias_indicators_llm' in formatted_results['analysis']:
             formatted_results['analysis']['bias_indicators'] = formatted_results['analysis'].pop('bias_indicators_llm')

        print(f"Analysis pipeline completed in {time.time() - start_time:.2f} seconds.")
        return formatted_results

    except ValueError as ve: print(f"ValueError during analysis pipeline: {ve}"); return {"error": f"{ve}"}
    except Exception as e: print(f"Unexpected error during analysis pipeline: {e}"); traceback.print_exc(); return {"error": f"An unexpected analysis error occurred: {getattr(e, 'message', str(e))}"}

# ----------------------------------------------------------------------------
# FLASK ROUTES
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
         if isinstance(results.get('analysis'), dict) and "raw_response" in results['analysis']: print(f"LLM Raw Response leading to error:\n{results['analysis']['raw_response']}")
         elif "error" in results: print(f"Analysis pipeline error: {results.get('error')}")
         return jsonify({"error": results["error"]}), 500
    add_to_history(input_type, input_value.strip(), results) # Use add_to_history
    return jsonify(results)

# --- NEW HISTORY DELETION ROUTES ---
@app.route('/history/delete/<int:item_id>', methods=['DELETE'])
def delete_history_item(item_id):
    """Deletes a specific item from the history."""
    print(f"Attempting to delete history item with ID: {item_id}")
    history = load_history()
    # Filter out the item with the matching ID
    # Make sure IDs loaded from JSON are integers for comparison
    original_length = len(history)
    history = [item for item in history if item.get('id') != item_id]

    if len(history) < original_length:
        if save_history_file(history):
            print(f"Successfully deleted item {item_id}.")
            return jsonify({"success": True, "message": "History item deleted."}), 200
        else:
            print(f"Error saving history file after attempting to delete item {item_id}.")
            return jsonify({"success": False, "error": "Failed to save updated history."}), 500
    else:
        print(f"Item with ID {item_id} not found in history.")
        return jsonify({"success": False, "error": "Item not found."}), 404

@app.route('/history/clear', methods=['DELETE'])
def clear_history():
    """Clears all items from the history."""
    print("Attempting to clear all history...")
    if save_history_file([]): # Save an empty list
        print("History cleared successfully.")
        return jsonify({"success": True, "message": "History cleared."}), 200
    else:
        print("Error saving empty history file.")
        return jsonify({"success": False, "error": "Failed to clear history."}), 500
# --- END NEW ROUTES ---

# ----------------------------------------------------------------------------
# MAIN EXECUTION
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)
