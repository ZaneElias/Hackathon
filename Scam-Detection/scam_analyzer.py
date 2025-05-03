# scam_analyzer.py
import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Language-specific prompts (optimized for each language)
LANGUAGE_PROMPTS = {
    "English": "Analyze this message for scams. Classify as: Safe/Suspicious/Scam. Explain in 1 line.",
    "Spanish": "Analiza este mensaje en busca de estafas. Clasifícalo como: Seguro/Sospechoso/Estafa. Explica en 1 línea.",
    "French": "Analysez ce message pour détecter les arnaques. Classez-le comme: Sûr/Suspect/Arnaque. Expliquez en 1 ligne."
}

def detect_scam(message, language="English"):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["English"])},
                {"role": "user", "content": f"Message: {message}"}
            ],
            temperature=0.3,  # Lower temp for stricter classification
            max_tokens=150
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error: {str(e)}"