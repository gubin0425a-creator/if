import os
import sys
import requests

# Ensure UTF-8 printing
sys.stdout.reconfigure(encoding='utf-8')

class VoiceGenerator:
    def __init__(self):
        self.tts_provider = os.getenv("TTS_PROVIDER", "openai").lower()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        
    def generate_voice(self, text, output_path):
        """
        Generates an audio file from text using OpenAI TTS or ElevenLabs.
        """
        output_path = os.path.abspath(output_path)
        print(f"[Voice] Generating voice using {self.tts_provider.upper()} for text: '{text[:20]}...'")
        
        if self.tts_provider == "elevenlabs":
            return self._generate_elevenlabs(text, output_path)
        else:
            return self._generate_openai(text, output_path)
            
    def _generate_openai(self, text, output_path):
        if not self.openai_api_key or "your_openai_key" in self.openai_api_key:
            raise ValueError("OpenAI API key is missing in .env file.")
            
        voice = os.getenv("OPENAI_VOICE", "nova") # 'nova' is energetic and fits a 10s female well
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "tts-1",
            "input": text,
            "voice": voice
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"[Voice] Voice saved successfully to: {output_path}")
            return True
        else:
            raise Exception(f"OpenAI TTS API failed with status {response.status_code}: {response.text}")
            
    def _generate_elevenlabs(self, text, output_path):
        if not self.elevenlabs_api_key or "your_elevenlabs_key" in self.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key is missing in .env file.")
            
        # ElevenLabs default Korean-friendly young female voice ID (or Bella)
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL") # Bella Voice ID
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.elevenlabs_api_key,
            "Content-Type": "application/json"
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"[Voice] ElevenLabs voice saved to: {output_path}")
            return True
        else:
            raise Exception(f"ElevenLabs API failed with status {response.status_code}: {response.text}")
