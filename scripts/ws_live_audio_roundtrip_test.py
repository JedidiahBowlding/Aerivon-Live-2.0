import asyncio
import base64
import json
from pathlib import Path

import websockets

WS_URL = f"wss://aerivon-live-agent-oauob6cvnq-uc.a.run.app/ws/live"
PCM_FILE = Path("/tmp/aerivon_spoken_test_input.pcm")


async def main() -> None:
    pcm = PCM_FILE.read_bytes()
    if not pcm:
        raise RuntimeError(f"audio input file is empty: {PCM_FILE}")

    statuses: list[str] = []
    in_transcripts: list[str] = []
    out_transcripts: list[str] = []
    out_audio_chunks = 0
    got_turn_complete = False

    async with websockets.connect(WS_URL, max_size=8_000_000) as ws:
        # Optional text priming helps the model respond after ASR.
        await ws.send(json.dumps({"type": "text", "text": "Transcribe the audio and answer briefly."}))

        chunk_size = 8192
        for i in range(0, len(pcm), chunk_size):
            chunk = pcm[i : i + chunk_size]
            await ws.send(
                json.dumps(
                    {
                        "type": "audio",
                        "mime_type": "audio/pcm;rate=16000",
                        "data_b64": base64.b64encode(chunk).decode("ascii"),
                    }
                )
            )
        await ws.send(json.dumps({"type": "audio_end"}))

        for _ in range(240):
            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(msg)
            msg_type = data.get("type")

            if msg_type == "status":
                statuses.append(str(data.get("status") or ""))
            elif msg_type == "transcript":
                tx = str(data.get("text") or "").strip()
                if tx:
                    out_transcripts.append(tx)
            elif msg_type == "text":
                tx = str(data.get("text") or "").strip()
                if tx:
                    in_transcripts.append(tx)
            elif msg_type == "audio" and data.get("data_b64"):
                out_audio_chunks += 1
            elif msg_type == "turn_complete":
                got_turn_complete = True
                break

    print("statuses=", statuses)
    print("input_pcm_bytes=", len(pcm))
    print("output_audio_chunks=", out_audio_chunks)
    print("sample_server_transcript=", out_transcripts[:1])
    print("sample_server_text=", in_transcripts[:1])
    print("turn_complete=", got_turn_complete)


if __name__ == "__main__":
    asyncio.run(main())
