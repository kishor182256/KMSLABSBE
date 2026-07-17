import math
import wave
from pathlib import Path
from uuid import uuid4

import lameenc

from app.application_core.application_settings import settings
from app.application_core.metadata_storage import ensure_runtime_dirs
from app.voice_engines.voice_engine_base import VoiceEngine, VoiceOptions


class PlaceholderVoiceEngine(VoiceEngine):
    name = "dummy"
    sample_rate = 22050

    def clone(self, voice_id: str, text: str, options: VoiceOptions) -> str:
        ensure_runtime_dirs()
        suffix = options.output_format.lstrip(".").lower() or "wav"
        output_path = Path(settings.output_dir) / f"{voice_id}_{uuid4().hex}.{suffix}"
        pcm_audio = self._generate_placeholder_pcm(text=text, speed=options.speed)
        if suffix == "mp3":
            self._write_mp3(output_path, pcm_audio)
        else:
            self._write_wav(output_path, pcm_audio)
        return str(output_path)

    def _generate_placeholder_pcm(self, text: str, speed: float) -> bytes:
        words = max(1, len(text.split()))
        duration_seconds = max(1.2, min(8.0, words / max(speed, 0.25) / 12))
        total_samples = int(self.sample_rate * duration_seconds)
        samples = bytearray()

        for index in range(total_samples):
            t = index / self.sample_rate
            envelope = min(1.0, index / (self.sample_rate * 0.08), (total_samples - index) / (self.sample_rate * 0.12))
            carrier = math.sin(2 * math.pi * 190 * t)
            overtone = 0.35 * math.sin(2 * math.pi * 380 * t)
            pulse = 0.55 + 0.45 * math.sin(2 * math.pi * 3.2 * t)
            value = int(12000 * envelope * pulse * (carrier + overtone))
            samples.extend(value.to_bytes(2, byteorder="little", signed=True))

        return bytes(samples)

    def _write_wav(self, output_path: Path, pcm_audio: bytes) -> None:
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_audio)

    def _write_mp3(self, output_path: Path, pcm_audio: bytes) -> None:
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(128)
        encoder.set_in_sample_rate(self.sample_rate)
        encoder.set_channels(1)
        encoder.set_quality(2)
        mp3_audio = encoder.encode(pcm_audio) + encoder.flush()
        output_path.write_bytes(mp3_audio)
