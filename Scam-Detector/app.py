# app.py - COMPLETE VERSION WITH URL CHECKING
import streamlit as st
from voice_utils import transcribe_audio, speak_text
from huggingface_hub import login
import tempfile
import os
import re
import requests
from typing import Tuple
from langdetect import detect, LangDetectException
from dotenv import load_dotenv
login(token=st.secrets.HUGGINGFACE_TOKEN)


# Load environment variables
load_dotenv()

# ===== CONFIGURATION =====
WHATSAPP_TRIGGERS = {
    "whatsapp verification": 70,
    "whatsapp premium": 65,
    "forwarded many times": 40
}

# ===== ENHANCED SCAM TRIGGERS =====
CRITICAL_TRIGGERS = {
    **WHATSAPP_TRIGGERS  # Add WhatsApp patterns
}

def is_malicious_url(url: str) -> bool:
    """Basic scam URL detection without API"""
    scam_tlds = {".xyz", ".icu", ".top", ".cfd", ".buzz"}
    suspicious_keywords = {"verify", "secure", "account", "bank"}
    
    url_lower = url.lower()
    
    # Check for scam TLDs
    if any(url_lower.endswith(tld) for tld in scam_tlds):
        return True
        
    # Check for suspicious keywords in domain
    domain_parts = url_lower.split("//")[-1].split("/")[0].split(".")
    if any(keyword in part for part in domain_parts for keyword in suspicious_keywords):
        return True
    
    return False

# Regex patterns for scam detection
BANK_PHISHING = re.compile(r'(banking|password|account)\s+(verification|update|alert)', re.IGNORECASE)
FAKE_LINK = re.compile(
    r'https?://(?:www\.)?(?!official-site\.com|banque-france\.fr)[a-z0-9-]+\.[a-z]{2,}', 
    re.IGNORECASE
)
ROLE_SCAM = re.compile(r'(tech support|IRS|Microsoft|admin)', re.IGNORECASE)
THREAT_COMBO = re.compile(r'(urgent|immediate action|suspended|terminate)', re.IGNORECASE)

def analyze_text(input_data) -> Tuple[bool, int, str, str]:
    # Handle both dict and string inputs
    if isinstance(input_data, dict):
        text = input_data.get('text', '')
    else:
        text = str(input_data)
    
    if not text.strip():
        return False, 0, "no input", "en"
    
    text_lower = text.lower()
    reasons = []
    confidence = 0

    # Check keyword triggers
    for trigger, weight in CRITICAL_TRIGGERS.items():
        if trigger in text_lower:
            confidence += weight
            reasons.append(trigger)

    # Regex checks
    if BANK_PHISHING.search(text):
        confidence += 45
        reasons.append("bank phishing")
    if FAKE_LINK.search(text):
        confidence += 40
        reasons.append("fake link")
    if ROLE_SCAM.search(text):
        confidence += 35
        reasons.append("role scam")
    if THREAT_COMBO.search(text):
        confidence += 80
        reasons.append("threat combo")

    # URL safety check (FIXED INDENTATION)
    urls = re.findall(r'https?://\S+', text)
    for url in urls:
        if is_malicious_url(url):
            confidence += 80
            reasons.append("malicious url")

    # Language detection
    try:
        lang = detect(text)[:2]
    except LangDetectException:
        lang = "en"

    confidence = min(100, max(0, confidence))
    is_scam = confidence >= 50
    
    return is_scam, confidence, " + ".join(sorted(set(reasons))), lang

def main():
    st.title("🛡️ Multi-Language Scam Shield")
    
    # Language selector
    lang = st.radio("Output Language:", ["English", "Spanish", "French"], index=0, horizontal=True)
    lang_code = {"English": "en", "Spanish": "es", "French": "fr"}[lang]
    
    # Tabbed interface
    tab1, tab2, tab3 = st.tabs(["Text", "Voice", "URL"])
    
    with tab1:
        user_input = st.text_area("Enter suspicious text:", height=150)
        if st.button("Analyze Text"):
            if user_input.strip():
                with st.spinner("Analyzing..."):
                    is_scam, confidence, reasons, detected_lang = analyze_text(user_input)
                    if is_scam:
                        threat_level = "CRITICAL" if confidence > 85 else "WARNING"
                        st.error(f"""🚨 {threat_level} THREAT DETECTED
                        \nReason: {reasons}
                        \nConfidence: {confidence}%""")
                        speak_text(f"{threat_level} threat detected: {reasons}", lang_code)
                    else:
                        st.success(f"""✅ SAFE MESSAGE
                        \nConfidence: {100-confidence}%""")
                        speak_text("No threats detected", lang_code)
            else:
                st.warning("Please enter text to analyze")
    
    with tab2:
        audio_file = st.file_uploader("Upload voice note:", type=["mp3", "wav"])
        if audio_file and st.button("Transcribe"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_file.read())
                tmp_path = tmp.name
            
            with st.spinner("Processing..."):
                result = transcribe_audio(tmp_path)
                transcribed_text = result.get('text', '')
                st.text_area("Transcription:", transcribed_text, height=100)
                if transcribed_text:
                    is_scam, confidence, reasons, detected_lang = analyze_text(transcribed_text)
                    if is_scam:
                        threat_level = "CRITICAL" if confidence > 85 else "WARNING"
                        st.error(f"""🚨 {threat_level} THREAT DETECTED
                        \nReason: {reasons}
                        \nConfidence: {confidence}%""")
                        speak_text(f"{threat_level} threat detected: {reasons}", lang_code)
                    else:
                        st.success(f"""✅ SAFE MESSAGE
                        \nConfidence: {100-confidence}%""")
                        speak_text("No threats detected", lang_code)
    
    with tab3:
        url = st.text_input("Enter URL to check:")
        if st.button("Check URL Safety"):
            if url:
                if is_malicious_url(url):
                    st.error("🚨 Dangerous URL Detected!")
                    speak_text("Dangerous URL detected", lang_code)
                else:
                    st.success("✅ Safe URL")
                    speak_text("This URL appears safe", lang_code)
            else:
                st.warning("Please enter a URL")

if __name__ == "__main__":
    main()
                    speak_text("This URL appears safe", lang_code)
            else:
                st.warning("Please enter a URL")

if __name__ == "__main__":
    main()
