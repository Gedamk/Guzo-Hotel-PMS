# -*- coding: utf-8 -*-
"""
sustainability_tips.py – Guzo Guest Assist Eco Awareness (v1.0)
---------------------------------------------------------------
Displays random sustainability / eco tips at the end of messages.
Promotes global hospitality green practices.
"""

import random

ENGLISH_TIPS = [
    "♻️ Eco Tip: Reuse towels to help save water.",
    "🌿 Eco Tip: Turn off lights and AC when leaving your room.",
    "💧 Eco Tip: Every drop counts — conserve water!",
    "🌎 Eco Tip: Support local produce in our restaurant.",
]

AMHARIC_TIPS = [
    "♻️ ኢኮ ምክር፦ እባክዎ ውሃን ለመቆጠብ ታውሎችን ይድገሙ።",
    "🌿 ኢኮ ምክር፦ ቤት ሲወጡ መብራትና ኤሲን ይጥፉ።",
    "💧 ኢኮ ምክር፦ እያንዳንዱ ጠብታ ውሃ አስፈላጊ ነው።",
    "🌎 ኢኮ ምክር፦ በሬስቶራንታችን አካባቢ የተመረቱ ምግቦችን ይመርጡ።",
]

def random_tip(lang="en"):
    """Return a random eco tip in the selected language."""
    tips = ENGLISH_TIPS if lang == "en" else AMHARIC_TIPS
    return random.choice(tips)
