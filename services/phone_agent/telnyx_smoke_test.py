"""
Standalone smoke test for Telnyx hosted STT/TTS — no pipecat required.

Mirrors exactly what TelnyxTTSService / TelnyxSTTService do (same endpoints,
request shapes, voice/model defaults, and MP3 -> 8 kHz ffmpeg decode), so a PASS
here means the service contracts are correct before we flip the live pipeline.

Round trip:
  1. TTS: POST text -> MP3 (audio/mpeg, output_type=binary_output)
  2. ffmpeg-decode MP3 -> 8 kHz S16LE mono PCM (the telephony rate), wrap as WAV
  3. STT: POST that 8 kHz WAV -> transcript, compare to the input text

Run (the key never appears in output or argv):
  ! cd /root/canada-trim/services/phone_agent && TELNYX_API_KEY=sk_... python3 telnyx_smoke_test.py
Optional:
  --text "..."  --voice Telnyx.KokoroTTS.af_bella  --model deepgram/nova-3  --keep
"""
import argparse
import io
import os
import subprocess
import sys
import wave

import httpx

TELNYX_TTS_URL = "https://api.telnyx.com/v2/text-to-speech/speech"
TELNYX_STT_URL = "https://api.telnyx.com/v2/ai/audio/transcriptions"
DEFAULT_VOICE = os.getenv("TELNYX_TTS_VOICE", "Telnyx.KokoroTTS.af_bella")
TELEPHONY_RATE = 8000


def _ffmpeg_mp3_to_pcm8k(mp3: bytes) -> bytes:
    """Decode MP3 -> 8 kHz signed-16-bit LE mono PCM via ffmpeg (mirrors the service)."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", str(TELEPHONY_RATE), "pipe:1"],
        input=mp3, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        print(f"[mix] FAIL ffmpeg rc={proc.returncode}: {proc.stderr.decode()[:400]}")
        sys.exit(1)
    return proc.stdout


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
    mp3 = res.content
    ctype = res.headers.get("content-type", "?")
    print(f"[TTS] OK  {len(mp3)} bytes  content-type={ctype}")
    if len(mp3) < 500:
        print("[TTS] WARN: response very short — voice id may be invalid (check dashboard)")
    return mp3


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

    mp3 = run_tts(key, args.text, args.voice)
    pcm8 = _ffmpeg_mp3_to_pcm8k(mp3)
    wav8 = _wav_bytes(pcm8, TELEPHONY_RATE)
    secs = (len(pcm8) / 2) / TELEPHONY_RATE
    print(f"[mix] ffmpeg MP3->8k mono, wrapped WAV ({len(wav8)} bytes ~{secs:.2f}s @ {TELEPHONY_RATE} Hz)\n")

    transcript = run_stt(key, wav8, args.model)

    if args.keep:
        with open("/tmp/telnyx_tts.mp3", "wb") as f:
            f.write(mp3)
        with open("/tmp/telnyx_8k.wav", "wb") as f:
            f.write(wav8)
        print("\n[keep] wrote /tmp/telnyx_tts.mp3 and /tmp/telnyx_8k.wav")

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
