import os
import base64
import requests
import json
import logging
from typing import Optional
import google.generativeai as genai
from config.config import config

logger = logging.getLogger(__name__)

# Configuration
ULCA_ENDPOINT = "https://meity-auth.ulcacontrib.org/ulca/apis/asr/v1/model/compute"
MODEL_ID = "6411741c56e9de23f65b5421"
SOURCE_LANG = "ur"

class UrduASR:
    """Urdu Automatic Speech Recognition using ULCA API"""

    def __init__(self):
        self.model_id = MODEL_ID
        self.source_lang = SOURCE_LANG
        self.endpoint = ULCA_ENDPOINT

    def file_to_base64(self, path):
        """Convert file to base64 encoding"""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def transcribe_audio(self, audio_path):
        """Transcribe audio to text using ULCA API"""
        try:
            audio_b64 = self.file_to_base64(audio_path)

            payload = {
                "modelId": self.model_id,
                "task": "asr",
                "source": self.source_lang,
                "audioContent": audio_b64,
                "userId": None
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "*/*",
            }

            response = requests.post(self.endpoint, headers=headers,
                                   data=json.dumps(payload), timeout=180)

            resp_json = response.json()
            transcription = None

            if "data" in resp_json:
                data = resp_json["data"]
                if isinstance(data, dict):
                    if "source" in data:
                        transcription = data["source"]
                    else:
                        outputs = data.get("output") or []
                        if outputs and isinstance(outputs, list):
                            transcription = outputs[0].get("source")

            elif "output" in resp_json:
                outputs = resp_json["output"]
                if outputs and isinstance(outputs, list):
                    transcription = outputs[0].get("source")

            if transcription:
                logger.info(f"Urdu transcription: {transcription}")
                return transcription.strip()
            return None

        except Exception as e:
            logger.error(f"ASR transcription failed: {e}")
            return None

async def translate_to_english(urdu_text: str) -> str:
    """Convert Urdu text to English using Gemini AI"""
    if not config.GEMINI_API_KEY:
        logger.warning("No Gemini API key found, returning original text")
        return urdu_text

    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""Convert this Urdu text to natural conversational English: "{urdu_text}"
        
        Rules:
        - Use natural and conversational English
        - Be accurate with the translation
        - Keep it concise but informative
        - Make it sound natural for healthcare requests
        
        Respond only in English."""
        
        response = model.generate_content(prompt)
        english_text = response.text.strip()
        logger.info(f"English translation: {english_text}")
        return english_text

    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return urdu_text

async def translate_to_urdu(english_text: str) -> str:
    """Convert English text to Urdu using Gemini AI"""
    if not config.GEMINI_API_KEY:
        logger.warning("No Gemini API key found, returning original text")
        return english_text

    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""Convert this English text to natural, contextual Urdu: "{english_text}"
        
        Rules:
        - Use proper Urdu script (not Roman Urdu)
        - Make it sound natural and fluent
        - Maintain the original meaning and tone
        - Use appropriate Pakistani healthcare terminology
        - Keep it formal but accessible
        
        Respond ONLY with the Urdu translation."""
        
        response = model.generate_content(prompt)
        urdu_text = response.text.strip()
        logger.info(f"Urdu translation: {urdu_text}")
        return urdu_text

    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return english_text

# Global voice service instances
urdu_asr = UrduASR()
