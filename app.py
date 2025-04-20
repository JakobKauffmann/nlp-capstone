# ----------------------------------------------------------------------------
# IMPORTS
# ----------------------------------------------------------------------------
from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime
import time
import statistics
import traceback
import random
import requests # For Hugging Face API calls

# Import web scraping functions
# Ensure web_scraper/main.py is in the same directory or adjust import path
from web_scraper.main import scrape_article_content, fetch_articles_for_topic

# Import Together AI client and load environment variables
from together import Together
from dotenv import load_dotenv

# ----------------------------------------------------------------------------
# Load Environment Variables & Initialize API Clients
# ----------------------------------------------------------------------------
load_dotenv() # Load variables from .env file

# Together AI Client
together_api_key = os.getenv("TOGETHER_API_KEY")
if not together_api_key:
    print("FATAL: TOGETHER_API_KEY not found in environment variables.")
    print("Please create a .env file with TOGETHER_API_KEY=your_key")
    # In a real app, might raise an exception or return an error page
    exit(1) # Exit if key is missing for simplicity here
try:
    together_client = Together(api_key=together_api_key)
    print("Together AI client initialized successfully.")
except Exception as e:
    print(f"FATAL: Could not initialize Together AI client: {e}")
    exit(1)

# Hugging Face API Key and Headers
hf_api_key = os.getenv("HF_API_KEY")
if not hf_api_key:
    print("FATAL: HF_API_KEY not found in environment variables.")
    print("Please create a .env file with HF_API_KEY=your_key")
    exit(1) # Exit if key is missing
hf_headers = {"Authorization": f"Bearer {hf_api_key}"}
print("Hugging Face API Key loaded.")

# Define Model Endpoints and LLM Model
LLM_MODEL = "meta-llama/Llama-3-8b-chat-hf" # For Together AI (ensure this model is suitable)
HF_SENTIMENT_URL = "https://api-inference.huggingface.co/models/siebert/sentiment-roberta-large-english"
HF_BIAS_URL = "https://api-inference.huggingface.co/models/bucketresearch/politicalBiasBERT"

# ----------------------------------------------------------------------------
# Flask App Initialization
# ----------------------------------------------------------------------------
app = Flask(__name__)

# ----------------------------------------------------------------------------
# HISTORY HANDLING
# ----------------------------------------------------------------------------
HISTORY_FILE = os.path.join('static', 'data', 'history.json')

def load_history():
    """Load analysis history from JSON file. Create it if it doesn't exist."""
    history_dir = os.path.dirname(HISTORY_FILE)
    # Create directory if it doesn't exist
    if not os.path.exists(history_dir):
        try:
            os.makedirs(history_dir)
            print(f"Created directory: {history_dir}")
        except OSError as e:
            print(f"Error creating directory {history_dir}: {e}")
            return [] # Cannot proceed if directory creation fails
    # Create file if it doesn't exist
    if not os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
            print(f"Created empty history file: {HISTORY_FILE}")
            return []
        except IOError as e:
            print(f"Error creating history file {HISTORY_FILE}: {e}")
            return [] # Cannot proceed if file creation fails
    # Load history if file exists
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f: # Specify encoding
            history_data = json.load(f)
            # Basic validation: ensure it's a list
            if not isinstance(history_data, list):
                print(f"Warning: History file {HISTORY_FILE} is not a valid JSON list. Resetting.")
                return []
            return history_data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {HISTORY_FILE}: {e}. Resetting history.")
        return []
    except IOError as e:
        print(f"Error reading history file {HISTORY_FILE}: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error loading history: {e}")
        print(traceback.format_exc())
        return []

def save_to_history(input_type, input_value, results):
    """Save analysis results to history JSON file."""
    history = load_history()
    # Ensure results is a dictionary before accessing keys
    if not isinstance(results, dict):
        print("Error: Invalid results format for saving history.")
        return

    # Determine bias and sentiment labels and scores safely using .get()
    bias_label = results.get('bias', 'N/A')
    sentiment_label = results.get('sentiment', 'N/A')
    bias_value = results.get('bias_value', 0)
    sentiment_value = results.get('sentiment_value', 0)

    # Basic data type validation for scores
    if not isinstance(bias_value, (int, float)): bias_value = 0
    if not isinstance(sentiment_value, (int, float)): sentiment_value = 0

    entry = {
        # Use timestamp for potentially more robust unique ID
        'id': int(time.time() * 1000),
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'input_type': input_type,
        # Truncate input value reasonably for display
        'input_value': (input_value[:100] + '...') if isinstance(input_value, str) and len(input_value) > 100 else input_value,
        'results': { # Match the structure expected by base.html history loop
            'bias': bias_label.capitalize() if isinstance(bias_label, str) else 'N/A',
            'sentiment': sentiment_label.capitalize() if isinstance(sentiment_label, str) else 'N/A',
            # Store scores as integers 0-100
            'bias_value': int(bias_value),
            'sentiment_value': int(sentiment_value)
        }
    }
    history.insert(0, entry) # Add new entry at the beginning

    # Limit history size
    max_history = 20
    if len(history) > max_history:
        history = history[:max_history]

    # Save updated history
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f: # Specify encoding
            json.dump(history, f, indent=2)
    except IOError as e:
        print(f"Error writing history file {HISTORY_FILE}: {e}")
    except Exception as e:
        print(f"Unexpected error saving history: {e}")
        print(traceback.format_exc())


# ----------------------------------------------------------------------------
# API CALL FUNCTIONS (HF + Together AI)
# ----------------------------------------------------------------------------

def query_hf_api(api_url, text_input):
    """Generic function to query the Hugging Face Inference API with retries."""
    # Limit input size for HF API calls if needed (check model docs)
    max_hf_input_chars = 1000 # Example limit
    payload = {"inputs": text_input[:max_hf_input_chars]}
    max_retries = 3
    last_error = None
    response = None # Initialize response to None

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=hf_headers, json=payload, timeout=25) # Increased timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json() # Success
        except requests.exceptions.Timeout:
            last_error = f"Timeout connecting to {api_url}"
            print(f"Warning: {last_error} (Attempt {attempt+1}/{max_retries})")
        except requests.exceptions.RequestException as e:
            last_error = f"Failed to connect to {api_url}: {e}"
            print(f"Error querying HF API {api_url}: {e} (Attempt {attempt+1}/{max_retries})")
            # Check for specific errors like model loading (503)
            if response is not None and response.status_code == 503:
                 print("HF model might be loading, returning temporary error.")
                 # Return specific error immediately if model is loading
                 return {"error": "Model is currently loading, please try again shortly."}
        except Exception as e: # Catch other potential errors like JSON parsing in requests library itself
             last_error = f"Unexpected error during HF API request to {api_url}: {e}"
             print(last_error)

        # Wait before retry only if not the last attempt
        if attempt < max_retries - 1:
             print("Waiting before retry...")
             time.sleep(2 * (attempt + 1)) # Exponential backoff slightly
        else:
             print("Max retries exceeded for Hugging Face API.")
             return {"error": last_error or "Max retries exceeded for Hugging Face API."}

    # Should not be reached if loop logic is correct, but as fallback:
    return {"error": last_error or "Max retries exceeded for Hugging Face API."}


def get_sentiment_hf(text):
    """Gets sentiment using the HF Inference API."""
    print("Querying HF Sentiment API...")
    result = query_hf_api(HF_SENTIMENT_URL, text)
    # Check if the query function returned an error object
    if isinstance(result, dict) and "error" in result:
        return {"sentiment_label": "Error", "sentiment_score": 0, "error": result["error"]}
    try:
        # Expected successful response format: [[{'label': '...', 'score': ...}, ...]]
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            scores = result[0]
            if not scores: # Handle case where inner list is empty
                 return {"sentiment_label": "Error", "sentiment_score": 0, "error": "Empty result list from API"}
            # Find the label with the highest score
            best_prediction = max(scores, key=lambda x: x.get('score', 0)) # Use .get for safety
            return {
                "sentiment_label": best_prediction.get('label', 'Unknown').capitalize(),
                "sentiment_score": int(best_prediction.get('score', 0) * 100)
            }
        else:
             # Log unexpected format for debugging
             print(f"Unexpected HF Sentiment API response format: {result}")
             return {"sentiment_label": "Error", "sentiment_score": 0, "error": "Unexpected API response format"}
    except Exception as e:
        print(f"Error processing HF Sentiment response: {e}")
        print(traceback.format_exc())
        return {"sentiment_label": "Error", "sentiment_score": 0, "error": f"Processing error: {e}"}

def get_bias_hf(text):
    """Gets political bias using the HF Inference API."""
    print("Querying HF Bias API...")
    result = query_hf_api(HF_BIAS_URL, text)
    # Check if the query function returned an error object
    if isinstance(result, dict) and "error" in result:
        return {"bias_label": "Error", "bias_score": 0, "error": result["error"]}
    try:
        # Expected successful response format: [[{'label': '...', 'score': ...}, ...]]
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            scores = result[0]
            if not scores: # Handle case where inner list is empty
                 return {"bias_label": "Error", "bias_score": 0, "error": "Empty result list from API"}
            best_prediction = max(scores, key=lambda x: x.get('score', 0)) # Use .get for safety
            # Normalize label
            label_raw = best_prediction.get('label', 'Unknown')
            if label_raw.upper() == 'LEFT': bias_label = 'Left'
            elif label_raw.upper() == 'RIGHT': bias_label = 'Right'
            elif label_raw.upper() == 'CENTER': bias_label = 'Center'
            else: bias_label = label_raw.capitalize()

            return {
                "bias_label": bias_label,
                "bias_score": int(best_prediction.get('score', 0) * 100)
            }
        else:
            print(f"Unexpected HF Bias API response format: {result}")
            return {"bias_label": "Error", "bias_score": 0, "error": "Unexpected API response format"}
    except Exception as e:
        print(f"Error processing HF Bias response: {e}")
        print(traceback.format_exc())
        return {"bias_label": "Error", "bias_score": 0, "error": f"Processing error: {e}"}


def get_llm_features(text):
    """Gets summary, findings, indicators, etc., using the Together AI LLM."""
    if not text or not isinstance(text, str):
        return {"error": "Invalid text provided for LLM analysis."}

    # Limit input text length
    max_input_chars = 8000 # Adjust based on model context window and desired cost
    truncated_text = text[:max_input_chars]
    if len(text) > max_input_chars:
        print(f"Warning: Truncating input text from {len(text)} to {max_input_chars} chars for LLM.")

    # Prompt focusing only on LLM tasks
    prompt = f"""
Analyze the following text. Provide the output STRICTLY in JSON format with the specified keys.

**Text to Analyze:**
--- START TEXT ---
{truncated_text}
--- END TEXT ---

**Requested JSON Output Structure:**
{{
  "summary": "...",               // A concise, neutral summary of the text (approx. 3-5 sentences).
  "key_findings": [              // List of 3-5 key points or conclusions from the text.
    "Finding 1...",
    "Finding 2...",
    "..."
  ],
  "bias_indicators_llm": [       // List 2-4 specific phrases or arguments from the text that seem indicative of a potential bias (without classifying the bias itself).
    "Indicator 1...",
    "Indicator 2...",
    "..."
  ],
  "credibility_assessment": "...", // Brief assessment (e.g., "Appears credible", "Lacks sourcing", "Uses emotionally charged language", "Presents multiple viewpoints"). Provide a short justification.
  "recommended_searches": [      // List 3 related search terms for further exploration.
    "Search term 1...",
    "Search term 2...",
    "Search term 3..."
  ]
}}

**Instructions:**
- Analyze the text carefully based ONLY on the provided content.
- Adhere strictly to the JSON format requested, using the exact keys.
- Ensure all fields are populated. If a field cannot be determined, use "N/A" or an empty list.
- The summary should be neutral and objective.

Provide ONLY the JSON output, without any introductory text, explanations, or markdown formatting.
"""
    analysis_result = {"error": "LLM analysis failed."} # Default error

    try:
        print(f"Sending request to LLM: {LLM_MODEL} for generative features...")
        start_llm_time = time.time()

        # Use the Together AI client
        response = together_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, # Adjust temperature as needed
            max_tokens=1024, # Adjust based on expected output size
            # Consider adding response_format={"type": "json_object"} if supported
        )

        llm_duration = time.time() - start_llm_time
        print(f"LLM response received in {llm_duration:.2f} seconds.")

        # Extract content and parse JSON
        raw_response = response.choices[0].message.content
        print(f"Raw LLM Response:\n{raw_response[:500]}...") # Log beginning of response

        json_start = raw_response.find('{')
        json_end = raw_response.rfind('}') + 1

        if json_start != -1 and json_end != -1:
            json_string = raw_response[json_start:json_end]
            try:
                parsed_json = json.loads(json_string)
                # Basic validation of expected keys
                required_keys = ["summary", "key_findings", "credibility_assessment"]
                if all(key in parsed_json for key in required_keys):
                    analysis_result = parsed_json # Success!
                    print("Successfully parsed JSON response from LLM.")
                else:
                    print("Error: Parsed JSON missing required keys from LLM.")
                    analysis_result = {"error": "LLM response missing required fields.", "raw_response": raw_response}
            except json.JSONDecodeError as e:
                print(f"Error: Failed to decode JSON from LLM response: {e}")
                analysis_result = {"error": f"Invalid JSON received from LLM: {e}", "raw_response": raw_response}
        else:
            print("Error: Could not find JSON object in LLM response.")
            analysis_result = {"error": "No valid JSON object found in LLM response.", "raw_response": raw_response}

    except Exception as e:
        print(f"Error during Together AI API call: {e}")
        print(traceback.format_exc())
        analysis_result = {"error": f"API communication error: {e}"}

    return analysis_result


# ----------------------------------------------------------------------------
# CORE ANALYSIS PIPELINE FUNCTION (Hybrid)
# ----------------------------------------------------------------------------

def perform_analysis(input_type, input_value):
    """
    Performs analysis using web scraping, HF API (Bias/Sentiment), and Together AI (LLM features).
    Handles text, URL, and topic inputs, including aggregation.
    """
    start_time = time.time()
    final_results = {}
    articles_analyzed = [] # Store combined results for each article

    try:
        # 1. Get Text Content(s)
        texts_to_analyze = [] # List of dicts: {'text': ..., 'source_url': ...}
        if input_type == 'text':
            texts_to_analyze.append({'text': input_value, 'source_url': 'Direct Text Input'})
            final_results['source_display'] = "Direct Text Input"
        elif input_type == 'url':
            print(f"Scraping URL: {input_value}")
            article_text = scrape_article_content(input_value)
            # Check for scraping errors more robustly
            if not isinstance(article_text, str) or "error" in article_text.lower() or "no extractable" in article_text.lower():
                 error_msg = article_text if isinstance(article_text, str) else "Unknown scraping error"
                 raise ValueError(f"Scraping failed: {error_msg}")
            texts_to_analyze.append({'text': article_text, 'source_url': input_value})
            final_results['source_display'] = input_value
        elif input_type == 'topic':
            print(f"Fetching articles for topic: {input_value}")
            # Fetch articles using the function from web_scraper.main
            fetched_articles = fetch_articles_for_topic(input_value, max_articles=3) # Limit number of articles
            if not fetched_articles:
                 raise ValueError(f"Could not find articles for topic: {input_value}")

            valid_articles_count = 0
            for article in fetched_articles:
                content = article.get('content')
                url = article.get('url', 'Unknown URL')
                # Check content validity
                if content and isinstance(content, str) and "error" not in content.lower() and "no extractable" not in content.lower():
                    texts_to_analyze.append({'text': content, 'source_url': url})
                    valid_articles_count += 1
                else:
                    print(f"   -> Skipping article {url} due to scraping/content issue.")
            if not texts_to_analyze:
                 raise ValueError(f"Could not successfully get content for any articles for topic: {input_value}")
            final_results['source_display'] = f"Topic: {input_value} ({len(texts_to_analyze)} articles processed)"
        else:
            raise ValueError(f"Invalid input_type: {input_type}")

        # 2. Analyze each text block using the hybrid approach
        for i, item in enumerate(texts_to_analyze):
            print(f"--- Analyzing article {i+1} from: {item['source_url']} ---")
            text = item['text']
            # Initialize dict to store results for this article
            combined_analysis = {'source_url': item['source_url']}

            # --- Call HF APIs (Bias & Sentiment) ---
            # Consider running these in parallel if performance is critical (using asyncio or threading)
            sentiment_res = get_sentiment_hf(text)
            bias_res = get_bias_hf(text)

            # Log warnings/errors from HF APIs
            if "error" in sentiment_res: print(f"   -> Sentiment analysis warning/error: {sentiment_res['error']}")
            if "error" in bias_res: print(f"   -> Bias analysis warning/error: {bias_res['error']}")

            # Add results (even if errors) to the combined dict
            combined_analysis.update(sentiment_res)
            combined_analysis.update(bias_res)

            # --- Call Together AI LLM (Summary & other features) ---
            llm_res = get_llm_features(text)
            if "error" in llm_res:
                print(f"   -> LLM analysis warning/error: {llm_res['error']}")
                # Provide default values if LLM fails to ensure keys exist
                llm_defaults = { "summary": "N/A", "key_findings": [], "bias_indicators_llm": [], "credibility_assessment": "N/A", "recommended_searches": [] }
                combined_analysis.update(llm_defaults) # Update with defaults
                combined_analysis["llm_error"] = llm_res["error"] # Store the error message
            else:
                 combined_analysis.update(llm_res) # Update with successful LLM results

            # Add the combined results for this article to the list
            articles_analyzed.append(combined_analysis)


        # 3. Aggregate and Format Results for Frontend
        if not articles_analyzed:
             raise ValueError("No analysis results were generated.")

        # --- Prepare final structure expected by JavaScript ---
        formatted_results = {
            'analysis': {}, # Combined/Aggregated results go here
            'visualization_data': {}, # Data specifically for charts
            'source_display': final_results.get('source_display', 'N/A')
            # Top-level keys for convenience/history saving
            # These will be populated based on single/multiple article analysis below
        }

        # --- Aggregation Logic ---
        if len(articles_analyzed) == 1:
            # --- Single article analysis ---
            analysis_data = articles_analyzed[0]
            formatted_results['analysis'] = analysis_data # Pass the combined analysis dict

            # Extract main labels/scores for top-level access & history
            formatted_results['sentiment'] = analysis_data.get('sentiment_label', 'N/A')
            formatted_results['bias'] = analysis_data.get('bias_label', 'N/A')
            formatted_results['summary'] = analysis_data.get('summary', 'N/A') # Get summary from LLM part
            formatted_results['sentiment_value'] = analysis_data.get('sentiment_score', 0)
            formatted_results['bias_value'] = analysis_data.get('bias_score', 0)

            # Create simple distribution for Plotly based on HF scores
            sentiment_dist = {analysis_data.get('sentiment_label', 'N/A'): analysis_data.get('sentiment_score', 100)}
            bias_dist = {analysis_data.get('bias_label', 'N/A'): analysis_data.get('bias_score', 100)}
            # Add other labels with 0 score if needed for consistent chart appearance
            for s_label in ['Positive', 'Negative', 'Neutral']:
                 if s_label not in sentiment_dist: sentiment_dist[s_label] = 0
            for b_label in ['Left', 'Center', 'Right']:
                 if b_label not in bias_dist: bias_dist[b_label] = 0


        else:
            # --- Multiple articles analysis (topic) ---
            # Filter out articles with errors in critical fields (bias/sentiment labels) before aggregating stats
            valid_articles = [a for a in articles_analyzed if 'error' not in a.get('sentiment_label', 'Error').lower() and 'error' not in a.get('bias_label', 'Error').lower()]

            if not valid_articles: # Handle case where all articles had errors
                 print("Warning: All articles for topic analysis had errors in bias/sentiment.")
                 # Use the first article's data (which might contain errors) as a fallback display
                 analysis_data = articles_analyzed[0]
                 formatted_results['analysis'] = analysis_data
                 formatted_results['sentiment'] = analysis_data.get('sentiment_label', 'Error')
                 formatted_results['bias'] = analysis_data.get('bias_label', 'Error')
                 formatted_results['summary'] = analysis_data.get('summary', 'N/A')
                 formatted_results['sentiment_value'] = analysis_data.get('sentiment_score', 0)
                 formatted_results['bias_value'] = analysis_data.get('bias_score', 0)
                 sentiment_dist = {formatted_results['sentiment']: formatted_results['sentiment_value']}
                 bias_dist = {formatted_results['bias']: formatted_results['bias_value']}

            else:
                # Aggregate scores from valid articles
                avg_sentiment_score = statistics.mean([a.get('sentiment_score', 0) for a in valid_articles])
                avg_bias_score = statistics.mean([a.get('bias_score', 0) for a in valid_articles])

                # Determine overall label (most frequent from valid articles)
                sentiment_labels = [a.get('sentiment_label', 'N/A') for a in valid_articles]
                bias_labels = [a.get('bias_label', 'N/A') for a in valid_articles]
                overall_sentiment = statistics.mode(sentiment_labels) if sentiment_labels else 'N/A'
                overall_bias = statistics.mode(bias_labels) if bias_labels else 'N/A'

                # Combine summaries, findings, indicators etc. from ALL articles (even those with HF errors if LLM worked)
                combined_summary = "\n\n---\n\n".join([f"Article {i+1} ({a.get('source_url', '')}):\n{a.get('summary', 'N/A')}" for i, a in enumerate(articles_analyzed)])
                combined_findings = [f"[{a.get('bias_label', '?')}/{a.get('sentiment_label', '?')}] {finding}" for a in articles_analyzed for finding in a.get('key_findings', [])]
                combined_indicators = [f"[{a.get('bias_label', '?')}] {indicator}" for a in articles_analyzed for indicator in a.get('bias_indicators_llm', [])]
                overall_credibility = articles_analyzed[0].get('credibility_assessment', 'N/A') # Just take first for now
                combined_searches = list(set(s for a in articles_analyzed for s in a.get('recommended_searches', [])))

                # Populate the main analysis dict with aggregated/combined values
                formatted_results['analysis'] = {
                    'sentiment': overall_sentiment,
                    'sentiment_score': int(avg_sentiment_score),
                    'political_bias': overall_bias,
                    'political_bias_score': int(avg_bias_score),
                    'summary': combined_summary,
                    'key_findings': combined_findings[:10], # Limit length
                    'bias_indicators': combined_indicators[:10], # Use LLM indicators
                    'credibility_assessment': overall_credibility,
                    'recommended_searches': combined_searches[:5]
                }
                # Add top-level convenience keys
                formatted_results['sentiment'] = overall_sentiment
                formatted_results['bias'] = overall_bias
                formatted_results['summary'] = combined_summary
                formatted_results['sentiment_value'] = int(avg_sentiment_score)
                formatted_results['bias_value'] = int(avg_bias_score)

                # Aggregate distribution data for Plotly from valid articles
                sentiment_dist = {}
                for label in ['Positive', 'Neutral', 'Negative']:
                    scores = [a.get('sentiment_score', 0) for a in valid_articles if a.get('sentiment_label') == label]
                    sentiment_dist[label] = int(statistics.mean(scores)) if scores else 0
                bias_dist = {}
                for label in ['Left', 'Center', 'Right']:
                    scores = [a.get('bias_score', 0) for a in valid_articles if a.get('bias_label') == label]
                    bias_dist[label] = int(statistics.mean(scores)) if scores else 0


        # --- Final Formatting & Placeholders ---
        formatted_results['visualization_data'] = {
            'sentiment_distribution': sentiment_dist,
            'bias_distribution': bias_dist
        }
        # Placeholder Credibility Score (0-100) - LLM provides assessment text
        # We could try to map the assessment text to a score, but using random for now
        formatted_results['credibility_value'] = random.randint(30, 75)

        # Ensure scores are within 0-100
        formatted_results['sentiment_value'] = max(0, min(100, formatted_results.get('sentiment_value', 0)))
        formatted_results['bias_value'] = max(0, min(100, formatted_results.get('bias_value', 0)))

        # Rename LLM indicators key for JS consistency if needed (JS expects 'bias_indicators')
        if 'analysis' in formatted_results and 'bias_indicators_llm' in formatted_results['analysis']:
             formatted_results['analysis']['bias_indicators'] = formatted_results['analysis'].pop('bias_indicators_llm')

        print(f"Analysis pipeline completed in {time.time() - start_time:.2f} seconds.")
        return formatted_results

    # Catch exceptions during the overall pipeline execution
    except ValueError as ve: # Catch specific value errors (like scraping failed)
        print(f"ValueError during analysis pipeline: {ve}")
        return {"error": f"{ve}"} # Return the specific error message
    except Exception as e:
        print(f"Unexpected error during analysis pipeline: {e}")
        print(traceback.format_exc())
        # Return a generic error for unexpected issues
        return {"error": f"An unexpected analysis error occurred: {getattr(e, 'message', str(e))}"}


# ----------------------------------------------------------------------------
# FLASK ROUTES (Unchanged)
# ----------------------------------------------------------------------------
@app.route('/')
def index():
    """Renders the main page, passing the analysis history."""
    history = load_history()
    return render_template('index.html', history=history)

@app.route('/analyze', methods=['POST'])
def analyze_route():
    """Handles the POST request for analysis."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415

    data = request.json
    input_type = data.get('input_type')
    input_value = data.get('input_value')

    # Basic validation
    if not input_type or input_type not in ['text', 'url', 'topic']:
        return jsonify({"error": "Invalid input_type specified"}), 400
    if not input_value or not isinstance(input_value, str) or not input_value.strip():
        return jsonify({"error": "Input value cannot be empty"}), 400

    # Call the analysis function
    results = perform_analysis(input_type, input_value.strip())

    # Check if analysis returned an error
    if "error" in results:
         # Log raw response if available (might be nested in case of LLM error)
         if isinstance(results.get('analysis'), dict) and "raw_response" in results['analysis']:
             print(f"LLM Raw Response leading to error:\n{results['analysis']['raw_response']}")
         # Return the specific error message from the results dict
         return jsonify({"error": results["error"]}), 500 # Use 500 for server-side errors

    # Save successful analysis to history (using top-level keys)
    save_to_history(input_type, input_value.strip(), results)

    # Return successful results
    return jsonify(results)

# ----------------------------------------------------------------------------
# MAIN EXECUTION
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    # Set host='0.0.0.0' to make it accessible on your network
    # Debug=False is recommended for production
    app.run(host='0.0.0.0', port=8080, debug=True)
