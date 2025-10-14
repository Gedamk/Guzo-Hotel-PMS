# translate_message.py
from googletrans import Translator

translator = Translator()

def translate_to_english(text):
    """
    Automatically detect the language and translate to English.
    """
    try:
        result = translator.translate(text, dest="en")
        print(f"Ã°ÂÂÂ Detected language: {result.src} Ã¢ÂÂ Translated to English")
        return result.text
    except Exception as e:
        print("Ã¢ÂÂ Ã¯Â¸Â Translation failed:", e)
        return text  # fallback: return original text
