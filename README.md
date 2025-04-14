# nlp-capstone: AI-Powered Political Bias and Sentiment Detection Web App

## Overview

This project is a capstone project for CS 273: Natural Language Processing at SJSU focused on building a Python-based Flask web application designed to analyze news articles for political bias and sentiment. It leverages natural language processing techniques, including text classification with pre-trained models, zero-shot learning for bias detection, and large language model (LLM) based summarization.

The goal is to provide users with an intuitive interface to gain insights into the framing and tone of news content obtained from various sources.

## Features

Users can interact with the application in three ways:

1.  **Direct Text Input**: Paste a block of text directly into the application for analysis.
2.  **URL Input**: Provide a URL to an online news article. The application will scrape the content and analyze it.
3.  **Topic Input**: Submit a research topic. The application uses DuckDuckGo Search to find relevant articles, scrapes them, and provides an aggregated analysis.

The application outputs the following for the analyzed text:

* **Sentiment Analysis**: Classifies the text as Positive, Negative, or Neutral using a pre-trained model.
* **Political Bias Detection**: Assigns a political bias label (Left, Right, or Independent) using zero-shot classification with an LLM. Results are color-coded for clarity (e.g., Blue for Left, Red for Right, Yellow for Independent).
* **Summarization**: Generates a concise summary of the article text using an LLM.
* **User Feedback**: Provides status updates during processing.
