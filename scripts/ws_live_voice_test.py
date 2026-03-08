import asyncio
import json

import websockets

URL = "wss://aerivon-live-agent-oauob6cvnq-uc.a.run.app/ws/live"


async def main() -> None:
    audio_chunks = 0
    transcripts: list[str] = []
    texts: list[str] = []
    statuses: list[str] = []
    got_turn_complete = False

    async with websockets.connect(URL, max_size=8_000_000) as ws:
        await ws.send(
            json.dumps(
                {
                    "type": "text",
                    "text": "Please respond with one short sentence greeting.",
                }
            )
        )

        for _ in range(160):
            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(msg)
            msg_type = data.get("type")

            if msg_type == "status":
                statuses.append(str(data.get("status") or ""))
            elif msg_type == "audio" and data.get("data_b64"):
                audio_chunks += 1
            elif msg_type == "transcript":
                tx = str(data.get("text") or "").strip()
                if tx:
                    transcripts.append(tx)
            elif msg_type == "text":
                tx = str(data.get("text") or "").strip()
                if tx:
                    texts.append(tx)
            elif msg_type == "turn_complete":
                got_turn_complete = True
                break

    print("statuses=", statuses)
    print("audio_chunks=", audio_chunks)
    print("sample_transcript=", transcripts[:1])
    print("sample_text=", texts[:1])
    print("turn_complete=", got_turn_complete)


if __name__ == "__main__":
    asyncio.run(main())
