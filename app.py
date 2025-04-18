from flask import Flask, render_template, request, jsonify
import random
import time
import json
import os
from datetime import datetime

app = Flask(__name__)

# Fake data for testing UI
FAKE_SENTIMENTS = ["Positive", "Neutral", "Negative"]
FAKE_BIASES = ["Left", "Center", "Right"]

# Path to history file
HISTORY_FILE = 'static/data/history.json'


def load_history():
    """Load analysis history from JSON file. Create it if it doesn't exist."""
    if not os.path.exists(HISTORY_FILE):
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        # Create empty history file
        with open(HISTORY_FILE, 'w') as f:
            json.dump([], f)
        return []

    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading history: {e}")
        return []


def save_to_history(input_type, input_value, results):
    """Save analysis results to history JSON file."""
    history = load_history()

    # Create a history entry
    entry = {
        'id': len(history) + 1,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'input_type': input_type,
        'input_value': input_value[:50] + '...' if len(input_value) > 50 else input_value,
        'results': {
            'bias': results['bias'],
            'sentiment': results['sentiment'],
            'bias_value': results['bias_value'],
            'sentiment_value': results['sentiment_value']
        }
    }

    # Add to history and save
    history.insert(0, entry)  # Add at the beginning (newest first)

    # Keep only the most recent 20 entries
    if len(history) > 20:
        history = history[:20]

    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")


def get_fake_data(input_type, input_value):
    """Generate fake analysis data for testing UI."""
    # Simulate processing time
    time.sleep(2)

    # Random sentiment and bias
    sentiment = random.choice(FAKE_SENTIMENTS)
    bias = random.choice(FAKE_BIASES)

    # Random sentiment and bias values (0-100)
    sentiment_value = random.randint(10, 90)
    bias_value = random.randint(10, 90)
    credibility_value = random.randint(10, 90)

    # Generate fake summary
    if input_type == "text":
        summary = f"This is a fake summary of the provided text. The analysis suggests a {sentiment.lower()} sentiment with a {bias.lower()} political bias. The content appears to discuss various political and economic factors related to current events."
    elif input_type == "url":
        summary = f"This is a fake summary of the article at {input_value}. The content appears to have a {sentiment.lower()} sentiment with a {bias.lower()} political bias. The article discusses perspectives on policy implications and social impacts."
    else:  # topic
        summary = f"Based on multiple articles about '{input_value}', the overall sentiment is {sentiment.lower()} with a predominant {bias.lower()} political bias. Various sources present different perspectives on this topic."

    # Fake detailed indicators
    indicators = {
        "Left": [
            {"name": "Progressive terminology", "value": random.randint(10, 95)},
            {"name": "Conservative criticism", "value": random.randint(10, 95)},
            {"name": "Liberal source citations", "value": random.randint(10, 95)}
        ],
        "Right": [
            {"name": "Conservative terminology", "value": random.randint(10, 95)},
            {"name": "Liberal criticism", "value": random.randint(10, 95)},
            {"name": "Conservative source citations", "value": random.randint(10, 95)}
        ],
        "Center": [
            {"name": "Balanced terminology", "value": random.randint(10, 95)},
            {"name": "Multiple viewpoints", "value": random.randint(10, 95)},
            {"name": "Neutral source citations", "value": random.randint(10, 95)}
        ]
    }

    # Create fake visualization data
    viz_data = {
        "sentiment_distribution": {
            "Positive": random.randint(10, 90),
            "Neutral": random.randint(10, 90),
            "Negative": random.randint(10, 90)
        },
        "bias_distribution": {
            "Left": random.randint(10, 90),
            "Center": random.randint(10, 90),
            "Right": random.randint(10, 90)
        }
    }

    # Fake key findings
    key_findings = [
        f"The content shows a {bias.lower()}-leaning bias with frequent mentions of related policies.",
        f"{sentiment} sentiment is primarily directed toward political figures and policies.",
        "The source has a moderate track record for factual accuracy but shows clear editorial bias.",
        "Emotional language is used frequently to emphasize points, particularly when criticizing opponents."
    ]

    # Fake recommended searches
    recommended_searches = [
        f"{input_value} opposing viewpoints",
        f"{input_value} fact check",
        f"{input_value} historical context",
        f"{input_value} expert analysis"
    ]

    # For topic search, generate contrasting viewpoints
    contrasting_views = []
    if input_type == "topic":
        contrasting_views = [
            {
                "title": f"Left-leaning perspective on {input_value}",
                "source": "Example Left Source",
                "summary": f"This represents a left-leaning view on {input_value}. It emphasizes social impact and progressive solutions.",
                "bias": "Left",
                "sentiment": random.choice(FAKE_SENTIMENTS)
            },
            {
                "title": f"Right-leaning perspective on {input_value}",
                "source": "Example Right Source",
                "summary": f"This represents a right-leaning view on {input_value}. It focuses on economic factors and traditional values.",
                "bias": "Right",
                "sentiment": random.choice(FAKE_SENTIMENTS)
            },
            {
                "title": f"Centrist perspective on {input_value}",
                "source": "Example Centrist Source",
                "summary": f"This represents a centrist view on {input_value}. It attempts to balance multiple considerations.",
                "bias": "Center",
                "sentiment": random.choice(FAKE_SENTIMENTS)
            }
        ]

    return {
        "sentiment": sentiment,
        "bias": bias,
        "summary": summary,
        "bias_value": bias_value,
        "sentiment_value": sentiment_value,
        "credibility_value": credibility_value,
        "indicators": indicators[bias],
        "key_findings": key_findings,
        "visualization_data": viz_data,
        "recommended_searches": recommended_searches,
        "contrasting_views": contrasting_views
    }


@app.route('/')
def index():
    # Load history data
    history = load_history()
    return render_template('index.html', history=history)


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    input_type = data.get('input_type')
    input_value = data.get('input_value')

    if not input_value:
        return jsonify({"error": "Input cannot be empty"}), 400

    try:
        # Get fake analysis results
        results = get_fake_data(input_type, input_value)

        # Save to history
        save_to_history(input_type, input_value, results)

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
# from flask import Flask, render_template, request, jsonify
# import random
# import time
# import json
#
# app = Flask(__name__)
#
# # Fake data for testing UI
# FAKE_SENTIMENTS = ["Positive", "Neutral", "Negative"]
# FAKE_BIASES = ["Left", "Center", "Right"]
#
#
# def get_fake_data(input_type, input_value):
#     """Generate fake analysis data for testing UI."""
#     # Simulate processing time
#     time.sleep(2)
#
#     # Random sentiment and bias
#     sentiment = random.choice(FAKE_SENTIMENTS)
#     bias = random.choice(FAKE_BIASES)
#
#     # Generate fake summary
#     if input_type == "text":
#         summary = f"This is a fake summary of the provided text. The analysis suggests a {sentiment.lower()} sentiment with a {bias.lower()} political bias. The content appears to discuss various political and economic factors related to current events. Further analysis would require integration with the actual NLP models."
#     elif input_type == "url":
#         summary = f"This is a fake summary of the article at {input_value}. The content appears to have a {sentiment.lower()} sentiment with a {bias.lower()} political bias. The article discusses perspectives on policy implications and social impacts. This is placeholder text until the actual model integration is complete."
#     else:  # topic
#         summary = f"Based on multiple articles about '{input_value}', the overall sentiment is {sentiment.lower()} with a predominant {bias.lower()} political bias. Various sources present different perspectives on this topic, with some emphasizing economic impacts while others focus on social consequences."
#
#     # Create fake visualization data
#     viz_data = {
#         "sentiment_distribution": {
#             "Positive": random.randint(10, 90),
#             "Neutral": random.randint(10, 90),
#             "Negative": random.randint(10, 90)
#         },
#         "bias_distribution": {
#             "Left": random.randint(10, 90),
#             "Center": random.randint(10, 90),
#             "Right": random.randint(10, 90)
#         }
#     }
#
#     # Fake recommended searches
#     recommended_searches = [
#         f"{input_value} opposing viewpoints",
#         f"{input_value} fact check",
#         f"{input_value} historical context",
#         f"{input_value} expert analysis"
#     ]
#
#     # For topic search, generate contrasting viewpoints
#     contrasting_views = []
#     if input_type == "topic":
#         contrasting_views = [
#             {
#                 "title": f"Left-leaning perspective on {input_value}",
#                 "source": "Example Left Source",
#                 "summary": f"This represents a left-leaning view on {input_value}. It emphasizes social impact and progressive solutions, focusing on equity and community-centered approaches.",
#                 "bias": "Left",
#                 "sentiment": random.choice(FAKE_SENTIMENTS)
#             },
#             {
#                 "title": f"Right-leaning perspective on {input_value}",
#                 "source": "Example Right Source",
#                 "summary": f"This represents a right-leaning view on {input_value}. It focuses on economic factors and traditional values, highlighting individual responsibility and market-based solutions.",
#                 "bias": "Right",
#                 "sentiment": random.choice(FAKE_SENTIMENTS)
#             },
#             {
#                 "title": f"Centrist perspective on {input_value}",
#                 "source": "Example Centrist Source",
#                 "summary": f"This represents a centrist view on {input_value}. It attempts to balance multiple considerations, suggesting compromise solutions that incorporate elements from different political perspectives.",
#                 "bias": "Center",
#                 "sentiment": random.choice(FAKE_SENTIMENTS)
#             }
#         ]
#
#     return {
#         "sentiment": sentiment,
#         "bias": bias,
#         "summary": summary,
#         "visualization_data": viz_data,
#         "recommended_searches": recommended_searches,
#         "contrasting_views": contrasting_views
#     }
#
#
# @app.route('/')
# def index():
#     return render_template('index.html')
#
#
# @app.route('/analyze', methods=['POST'])
# def analyze():
#     data = request.json
#     input_type = data.get('input_type')
#     input_value = data.get('input_value')
#
#     if not input_value:
#         return jsonify({"error": "Input cannot be empty"}), 400
#
#     try:
#         # Get fake analysis results
#         results = get_fake_data(input_type, input_value)
#         return jsonify(results)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
#
#
# if __name__ == '__main__':
#     app.run(debug=True)