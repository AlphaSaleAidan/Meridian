"""
Twilio Media-Streams protocol harness for the phone-agent sidecar.

Unlike `phone_stream_harness.py` (which feeds raw PCM frames straight into the
pipeline), this drives the ACTUAL provider WebSocket the way Twilio does — the
`connected`/`start` prelude, then base64 **mu-law 8 kHz** `media` events — so it
exercises the `TwilioFrameSerializer` decode/encode path end-to-end against a
running sidecar. That's the path a real phone call takes, minus the PSTN leg.

It plays a two-turn call (order, then confirm) and collects the bot's outbound
`media` events (its TTS, re-encoded to mu-law by the serializer). The order tool
firing is confirmed in the sidecar logs (grep "Calling function [submit_order").

Prereqs:
  - sidecar running, e.g.:
      DEEPSEEK_API_KEY=... NVIDIA_API_KEY=... PHONE_PROVIDER=twilio \
        python -m uvicorn main:app --host 127.0.0.1 --port 8095
    (run without SUPABASE_* so merchant 'harness' resolves to the active demo config)
  - espeak-ng installed (caller audio)

Run:
  python tests/twilio_media_stream_harness.py [ws://host:port]
Exit 0 if the bot streamed audio back, else 1.
"""
import asyncio
import audioop
import base64
import json
import os
import subprocess
import sys
import tempfile
import wave

import websockets

DEFAULT_URI = "ws://127.0.0.1:8095/twilio/media-stream/harness"
TURN1 = "Hi, I'd like one double cheeseburger and a large fries for pickup. My name is Sam."
TURN2 = "Yes, that is correct. That's everything, thank you."
SID = "MZ_harness"


def _mulaw_frames(text: str) -> list[bytes]:
    """espeak → 8 kHz mono → mu-law → 160-byte (20 ms) frames."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    subprocess.run(["espeak-ng", "-v", "en-us", "-s", "150", "-w", path, text],
                   check=True, capture_output=True)
    w = wave.open(path)
    sr, pcm = w.getframerate(), w.readframes(w.getnframes())
    w.close()
    os.unlink(path)
    if sr != 8000:
        pcm, _ = audioop.ratecv(pcm, 2, 1, sr, 8000, None)
    ulaw = audioop.lin2ulaw(pcm, 2)
    return [ulaw[i:i + 160] for i in range(0, len(ulaw), 160)]


async def run(uri: str) -> dict:
    t1, t2 = _mulaw_frames(TURN1), _mulaw_frames(TURN2)
    result = {"outbound_media": 0, "outbound_bytes": 0}

    async with websockets.connect(uri, max_size=None) as ws:
        await ws.send(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))
        await ws.send(json.dumps({
            "event": "start", "sequenceNumber": "1", "streamSid": SID,
            "start": {
                "streamSid": SID, "callSid": "CA_harness", "accountSid": "AC_x",
                "customParameters": {"caller_phone": ""},
                "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
            },
        }))

        async def receiver():
            try:
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("event") == "media":
                        result["outbound_media"] += 1
                        result["outbound_bytes"] += len(base64.b64decode(msg["media"]["payload"]))
            except Exception:
                pass

        rx = asyncio.create_task(receiver())

        async def play(frames: list[bytes]):
            for n, fr in enumerate(frames):
                await ws.send(json.dumps({
                    "event": "media", "streamSid": SID,
                    "media": {"track": "inbound", "chunk": str(n), "timestamp": str(n * 20),
                              "payload": base64.b64encode(fr).decode()},
                }))
                await asyncio.sleep(0.02)
            silence = base64.b64encode(b"\xff" * 160).decode()  # 1.5 s mu-law silence → VAD endpoint
            for _ in range(75):
                await ws.send(json.dumps({"event": "media", "streamSid": SID,
                                          "media": {"track": "inbound", "payload": silence}}))
                await asyncio.sleep(0.02)

        await play(t1)
        await asyncio.sleep(15)   # bot reads the order back
        await play(t2)
        await asyncio.sleep(14)   # bot confirms + submits
        await ws.send(json.dumps({"event": "stop", "streamSid": SID}))
        await asyncio.sleep(1)
        rx.cancel()

    return result


def main() -> int:
    uri = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URI
    result = asyncio.run(run(uri))
    print("TWILIO_HARNESS " + json.dumps(result))
    ok = result["outbound_media"] > 0
    print(f"  [{'PASS' if ok else 'FAIL'}] bot streamed mu-law audio back "
          f"({result['outbound_media']} frames, {result['outbound_bytes']} bytes)")
    print("  (confirm submit_order in the sidecar log: grep 'Calling function \\[submit_order')")
    print("HARNESS " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
