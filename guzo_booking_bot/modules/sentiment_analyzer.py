# -*- coding: utf-8 -*-
"""
sentiment_analyzer.py – Guzo Guest Assist Guest Sentiment (v1.0)
----------------------------------------------------------------
Lightweight polarity-based sentiment analysis for guest messages.
Used to detect satisfaction and trigger admin alerts.
"""

from textblob import TextBlob

def analyze(text: str) -> str:
    """
    Analyze message sentiment.
    Returns: 'positive', 'neutral', or 'negative'
    """
    try:
        polarity = TextBlob(text).sentiment.polarity
        if polarity < -0.3:
            return "negative"
        elif polarity > 0.3:
            return "positive"
        return "neutral"
    except Exception:
        return "neutral"
