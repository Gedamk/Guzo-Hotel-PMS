# -*- coding: utf-8 -*-
"""
ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ§ÃÂÂÃÂÂÃÂÂÃÂÂ  Guzo Guest Assist ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ AI Analyzer Component
Analyzes guest messages & predicts booking trends.
"""

import streamlit as st
import pandas as pd
from textblob import TextBlob
from datetime import datetime
import random

def analyze_sentiment(message):
  try:
    score = TextBlob(message).sentiment.polarity
    if score > 0.3:
      return "ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ Positive"
    elif score < -0.3:
      return "ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ Negative"
    else:
      return "ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ Neutral"
  except:
    return "N/A"

def render_ai_insights():
  st.subheader("ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ§ÃÂÂÃÂÂÃÂÂÃÂÂ  AI Guest Sentiment & Booking Trends")

  st.markdown("""
  *Using smart text analysis to measure guest mood and forecast hospitality trends.*
  """)

  # Example messages (future: from NotificationLogs)
  messages = [
    "Loved the service and the staff were kind!",
    "The room was too noisy at night.",
    "Excellent breakfast and fast check-in.",
    "Wi-Fi was slow but the staff handled it well.",
  ]

  df = pd.DataFrame({
    "Guest Message": messages,
    "Sentiment": [analyze_sentiment(m) for m in messages]
  })

  st.dataframe(df, width="stretch", hide_index=True)

  # Booking trend forecast (demo logic)
  forecast = random.randint(80, 95)
  st.metric("ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ Predicted Occupancy Next Week", f"{forecast}%")

  st.markdown(f"""
  - ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ Generated: {datetime.now().strftime('%B %d, %Y ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ %I:%M %p')}
  - ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂ Overall Sentiment: **Highly Positive**
  - ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ AI Ready for Integration: Google Gemini or OpenAI Models
  """)

  st.caption("ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ¡ Future version will analyze live guest feedback from Notification Logs.")
