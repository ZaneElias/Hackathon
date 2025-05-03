# voice_utils.py
from huggingface_hub import hf_hub_download
import os
from faster_whisper import WhisperModel
import sys
import hashlib
import tempfile
import time
import threading
from typing import Optional, Dict
import torch
import pygame
from gtts import gTTS
from faster_whisper import WhisperModel, utils

# ===== SETUP LOGGING =====
utils.get_logger().setLevel("INFO")  # Enable progress logging

# ===== CONFIGURATION =====
MODEL_SIZE = "tiny"
LANGUAGE_MAP = {
    "en": "english",
    "es": "spanish",
    "fr": "french",
    "de": "german",
    "it": "italian"
}

# ===== AUDIO CACHE =====
class AudioCache:
    MAX_CACHE_SIZE = 20  # Limit cache to 20 items
    
    def __init__(self):
        self.cache = {}
        self.lru = []
        
    def get_key(self, text: str, lang: str) -> str:
        return hashlib.md5(f"{text}_{lang}".encode()).hexdigest()
    
    def store(self, text: str, lang: str, audio_path: str) -> None:
        key = self.get_key(text, lang)
        if key not in self.cache:
            if len(self.cache) >= self.MAX_CACHE_SIZE:
                oldest_key = self.lru.pop(0)
                del self.cache[oldest_key]
            self.cache[key] = audio_path
        self.lru.append(key)
        
    def retrieve(self, text: str, lang: str) -> Optional[str]:
        key = self.get_key(text, lang)
        if key in self.cache:
            # Update LRU
            if key in self.lru:
                self.lru.remove(key)
            self.lru.append(key)
            return self.cache[key]
        return None

# ===== AUDIO TRANSCRIBER =====
class AudioTranscriber:
    def __init__(self):
        # REPLACE THIS PART
        # Old code: MODEL_SIZE = "tiny"
        
        # New code for Hugging Face
        model_path = hf_hub_download(
            repo_id="ZaneElias/scamshield-whisper",
            filename="ggml-model-whisper-base.bin",
            cache_dir="models"
        )
        
        self.model = WhisperModel(
            model_path,  # Use downloaded model
            device="cpu",
            compute_type="int8"
        )  # Closing parenthesis added here
        print(f"Initialized transcriber on device: {self.device.upper()}")

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict:
        """Transcribe audio file to text."""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if language and language not in LANGUAGE_MAP:
            raise ValueError(f"Unsupported language. Supported: {list(LANGUAGE_MAP.keys())}")

        try:
            language = LANGUAGE_MAP.get(language)
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True  # Enable voice activity detection
            )
            
            return {
                "text": " ".join(segment.text for segment in segments),
                "language": info.language,
                "confidence": round(info.language_probability, 4)
            }
        except Exception as e:
            print(f"Transcription error: {str(e)}")
            return {
                "text": "",
                "language": "",
                "confidence": 0
            }

# ===== VOICE ENGINE =====
class VoiceEngine:
    def __init__(self):
        self.cache = AudioCache()
        pygame.mixer.init()
        self.lock = threading.Lock()
        self.running = True

    def _play_audio(self, file_path: str) -> None:
        """Thread-safe audio playback."""
        with self.lock:
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and self.running:
                    time.sleep(0.1)
            except pygame.error as e:
                print(f"Audio playback error: {str(e)}")

    def speak(self, text: str, lang: str = "en") -> None:
        """Convert text to speech and play audio."""
        if not text.strip():
            return

        try:
            # Try cache first
            cached_path = self.cache.retrieve(text, lang)
            if cached_path and os.path.exists(cached_path):
                self._play_audio(cached_path)
                return

            # Generate new audio
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                tts = gTTS(text=text, lang=lang, slow=False)
                tts.save(fp.name)
                self.cache.store(text, lang, fp.name)
                self._play_audio(fp.name)

        except Exception as e:
            print(f"TTS Error: {str(e)}")
            # Cross-platform fallback
            self._system_tts_fallback(text)

    def _system_tts_fallback(self, text: str) -> None:
        """Fallback to system TTS."""
        try:
            if sys.platform == "darwin":
                os.system(f'say "{text}"')
            elif sys.platform == "win32":
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Speak(text)
            else:
                print("System TTS not available for this platform")
        except Exception as fallback_error:
            print(f"Fallback TTS failed: {str(fallback_error)}")

    def cleanup(self) -> None:
        """Release resources."""
        self.running = False
        pygame.mixer.quit()

# ===== INITIALIZE COMPONENTS =====
transcriber = AudioTranscriber()
voice_engine = VoiceEngine()

# ===== PUBLIC API =====
def transcribe_audio(audio_path: str, language: Optional[str] = None) -> Dict:
    """
    Transcribe audio from file.
    
    Args:
        audio_path: Path to audio file
        language: Optional language code (en/es/fr/de/it)
    
    Returns:
        Dictionary with 'text', 'language', and 'confidence'
    """
    return transcriber.transcribe(audio_path, language)

def speak_text(text: str, lang: str = "en") -> None:
    """Convert text to speech and play immediately."""
    voice_engine.speak(text, lang)

def cleanup_voice_engine() -> None:
    """Cleanup resources when done."""
    voice_engine.cleanup()

# ===== TESTING =====
if __name__ == "__main__":
    # Example usage
    result = transcribe_audio("test_audio.wav")
    print("Transcription:", result)
    speak_text("Hello, this is a test of the voice system", "en")
    time.sleep(5)  # Wait for playback
    cleanup_voice_engine()
