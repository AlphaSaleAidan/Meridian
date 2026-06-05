"""
Standalone smoke test for Telnyx hosted STT/TTS — no pipecat required.

Mirrors exactly what TelnyxTTSService / TelnyxSTTService do (same endpoints,
request shapes, voice/model defaults, and 24 kHz -> 8 kHz resample), so a PASS
here means the service contracts are correct before we flip the live pipeline.

Round trip:
  1. TTS: POST text -> 24 kHz S16LE mono PCM (output_type=binary_output)
  2. resample 24k -> 8k (the telephony rate), wrap as WAV
  3. STT: POST that 8 kHz WAV -> transcript, compare to the input text

Run (the key never appears in output or argv):
  ! cd /root/canada-trim/services/phone_agent && TELNYX_API_KEY=sk_... python3 telnyx_smoke_test.py
Optional:
  --text "..."  --voice Telnyx.NaturalHD.astra  --model deepgram/nova-3  --keep
"""
import argparse
import io
import os
import sys
import wave

import httpx
import numpy as np
from scipy.signal import resample_poly

TELNYX_TTS_URL = "https://api.telnyx.com/v2/text-to-speech"
TELNYX_STT_URL = "https://api.telnyx.com/v2/ai/audio/transcriptions"
DEFAULT_VOICE = os.getenv("TELNYX_TTS_VOICE", "Telnyx.NaturalHD.astra")
TTS_NATIVE_RATE = 24000
TELEPHONY_RATE = 8000


def _resample_24k_to_8k(audio: np.ndarray) -> np.ndarray:
    return resample_poly(audio, 1, TTS_NATIVE_RATE // TELEPHONY_RATE)


def _pcm16_to_float(b: bytes) -> np.ndarray:
    if len(b) % 2:
        b = b[:-1]
    return np.frombuffer(b, dtype=np.int16).astype(np.float32) / 32768.0


def _float_to_pcm16(audio: np.ndarray) -> bytes:
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()


def _wav_bytes(pcm16: bytes, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm16)
    return buf.getvalue()


def run_tts(key: str, text: str, voice: str) -> bytes:
    print(f"[TTS] POST {TELNYX_TTS_URL}  voice={voice}")
    res = httpx.post(
        TELNYX_TTS_URL,
        json={"text": text, "voice": voice, "output_type": "binary_output"},
        headers={"Authorization": f"Bearer {key}"},
        timeout=30.0,
    )
    if res.status_code != 200:
        print(f"[TTS] FAIL {res.status_code}: {res.text[:400]}")
        sys.exit(1)
    pcm = res.content
    secs = (len(pcm) / 2) / TTS_NATIVE_RATE
    print(f"[TTS] OK  {len(pcm)} bytes  ~{secs:.2f}s @ {TTS_NATIVE_RATE} Hz S16LE mono")
    if secs < 0.2:
        print("[TTS] WARN: response shorter than 0.2s — voice id may be invalid (check dashboard)")
    return pcm


def run_stt(key: str, wav: bytes, model: str) -> str:
    print(f"[STT] POST {TELNYX_STT_URL}  model={model}")
    data = {"model": model, "response_format": "json"}
    if model.startswith("deepgram"):
        data["language"] = "en"
        data["model_config"] = '{"smart_format": true, "punctuate": true}'
    res = httpx.post(
        TELNYX_STT_URL,
        data=data,
        files={"file": ("utterance.wav", wav, "audio/wav")},
        headers={"Authorization": f"Bearer {key}"},
        timeout=30.0,
    )
    if res.status_code != 200:
        print(f"[STT] FAIL {res.status_code}: {res.text[:400]}")
        sys.exit(1)
    text = (res.json().get("text") or "").strip()
    print(f"[STT] OK  transcript: {text!r}")
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="Hi, thanks for calling Meridian. What can I get started for you today?")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--model", default="deepgram/nova-3")
    ap.add_argument("--keep", action="store_true", help="write wavs to /tmp for manual listening")
    args = ap.parse_args()

    key = os.getenv("TELNYX_API_KEY", "")
    if not key:
        print("ERROR: TELNYX_API_KEY not set in env")
        sys.exit(2)

    print(f"Round-trip text: {args.text!r}\n")

    pcm24 = run_tts(key, args.text, args.voice)
    audio8 = _resample_24k_to_8k(_pcm16_to_float(pcm24))
    wav8 = _wav_bytes(_float_to_pcm16(audio8), TELEPHONY_RATE)
    print(f"[mix] resampled 24k->8k, wrapped WAV ({len(wav8)} bytes @ {TELEPHONY_RATE} Hz)\n")

    transcript = run_stt(key, wav8, args.model)

    if args.keep:
        with open("/tmp/telnyx_tts_24k.wav", "wb") as f:
            f.write(_wav_bytes(pcm24, TTS_NATIVE_RATE))
        with open("/tmp/telnyx_8k.wav", "wb") as f:
            f.write(wav8)
        print("\n[keep] wrote /tmp/telnyx_tts_24k.wav and /tmp/telnyx_8k.wav")

    print()
    src = {w.lower().strip(".,!?") for w in args.text.split()}
    got = {w.lower().strip(".,!?") for w in transcript.split()}
    overlap = len(src & got) / max(len(src), 1)
    if transcript and overlap >= 0.5:
        print(f"PASS — round trip works ({overlap:.0%} word overlap). STT+TTS contracts are good.")
    elif transcript:
        print(f"PARTIAL — got a transcript but only {overlap:.0%} word overlap. "
              "Audio path works; check voice clarity / model.")
    else:
        print("FAIL — empty transcript. STT did not understand the synthesized audio.")
        sys.exit(1)


if __name__ == "__main__":
    main()
