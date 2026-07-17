import wave
from pathlib import Path

import lameenc


def encode_wav_file_to_mp3(source_wav_path: Path, target_mp3_path: Path, bit_rate: int = 128) -> None:
    with wave.open(str(source_wav_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        pcm_audio = wav_file.readframes(wav_file.getnframes())

    if sample_width != 2:
        raise ValueError("MP3 export requires 16-bit PCM WAV output from the voice engine.")

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bit_rate)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(channels)
    encoder.set_quality(2)
    target_mp3_path.write_bytes(encoder.encode(pcm_audio) + encoder.flush())
