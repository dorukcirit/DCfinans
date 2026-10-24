import os
from pathlib import Path
import subprocess
import sys
from typing import Dict, Optional
import requests


class TTSAudioEngine:
    """
    Üretilen TTS spiker metnini MP3 ses dosyasına dönüştürmek için genişletilebilir adaptör.
    Desteklenen motorlar:
    - 'edge-tts': Ücretsiz Microsoft Türkçe Nöral sesler (tr-TR-AhmetNeural / tr-TR-EmelNeural)
    - 'openai': OpenAI TTS API (OPENAI_API_KEY gerektirir)
    - 'elevenlabs': ElevenLabs API (ELEVENLABS_API_KEY gerektirir)
    """

    def __init__(self, tts_config: Optional[Dict] = None):
        self.config = tts_config or {}
        self.engine = self.config.get("motor", "edge-tts")
        self.voice = self.config.get("ses_kodu", "tr-TR-AhmetNeural")
        self.rate = self.config.get("konusma_hizi", "+5%")

    def synthesize_to_mp3(self, tts_text_path: Path, output_mp3_path: Path) -> tuple[bool, str]:
        """
        Normalize edilmiş TTS metin dosyasını MP3'e çevirir.
        Dönüş: (basarili_mi, mesaj)
        """
        if self.engine == "edge-tts":
            return self._run_edge_tts(tts_text_path, output_mp3_path)
        elif self.engine == "openai":
            return self._run_openai_tts(tts_text_path, output_mp3_path)
        elif self.engine == "elevenlabs":
            return self._run_elevenlabs_tts(tts_text_path, output_mp3_path)
        return False, f"Bilinmeyen TTS motoru: {self.engine}"

    def _run_edge_tts(self, tts_text_path: Path, output_mp3_path: Path) -> tuple[bool, str]:
        try:
            cmd = [
                sys.executable,
                "-m",
                "edge_tts",
                "--voice",
                self.voice,
                f"--rate={self.rate}",
                "--file",
                str(tts_text_path),
                "--write-media",
                str(output_mp3_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0 and output_mp3_path.exists():
                return True, f"MP3 ses dosyası üretildi: {output_mp3_path}"
            return (
                False,
                "edge-tts kurulu değil veya çalıştırılamadı. Kurmak için: pip install edge-tts",
            )
        except Exception as exc:
            return False, f"edge-tts hatası: {exc}"

    def _run_openai_tts(self, tts_text_path: Path, output_mp3_path: Path) -> tuple[bool, str]:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return False, "OPENAI_API_KEY ortam değişkeni tanımlı değil."
        text = tts_text_path.read_text(encoding="utf-8")[:4096]
        try:
            resp = requests.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "tts-1-hd",
                    "voice": "onyx",
                    "input": text,
                },
                timeout=45,
            )
            if resp.status_code == 200:
                output_mp3_path.write_bytes(resp.content)
                return True, f"OpenAI TTS ile MP3 üretildi: {output_mp3_path}"
            return False, f"OpenAI TTS API hatası ({resp.status_code})"
        except Exception as exc:
            return False, f"OpenAI TTS bağlantı hatası: {exc}"

    def _run_elevenlabs_tts(self, tts_text_path: Path, output_mp3_path: Path) -> tuple[bool, str]:
        api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
        if not api_key:
            return False, "ELEVENLABS_API_KEY ortam değişkeni tanımlı değil."
        voice_id = self.config.get("elevenlabs_voice_id", "21m00Tcm4TlvDq8ikWAM")
        text = tts_text_path.read_text(encoding="utf-8")[:5000]
        try:
            resp = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                },
                timeout=45,
            )
            if resp.status_code == 200:
                output_mp3_path.write_bytes(resp.content)
                return True, f"ElevenLabs ile MP3 üretildi: {output_mp3_path}"
            return False, f"ElevenLabs API hatası ({resp.status_code})"
        except Exception as exc:
            return False, f"ElevenLabs bağlantı hatası: {exc}"
