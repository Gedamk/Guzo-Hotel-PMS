# -*- coding: utf-8 -*-
"""
ÃÃÃÃ°ÃÃÃÃÃÃÃÃ§ÃÃÃÃ  Guzo Guest Assist ÃÃÃÃÃÃÃÃÃÃÃÃ AI Analyzer Component
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
      return "ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Positive"
    elif score < -0.3:
      return "ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Negative"
    else:
      return "ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Neutral"
  except:
    return "N/A"

def render_ai_insights():
  st.subheader("ÃÃÃÃ°ÃÃÃÃÃÃÃÃ§ÃÃÃÃ  AI Guest Sentiment & Booking Trends")

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

  st.dataframe(df, use_container_width=True, hide_index=True)

  # Booking trend forecast (demo logic)
  forecast = random.randint(80, 95)
  st.metric("ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Predicted Occupancy Next Week", f"{forecast}%")

  st.markdown(f"""
  - ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Generated: {datetime.now().strftime('%B %d, %Y ÃÃÃÃÃÃÃÃÃÃÃÃ %I:%M %p')}
  - ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Overall Sentiment: **Highly Positive**
  - ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ AI Ready for Integration: Google Gemini or OpenAI Models
  """)

  st.caption("ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ¡ Future version will analyze live guest feedback from Notification Logs.")
