import asyncio
import json
import websockets

URL = "wss://aerivon-live-agent-oauob6cvnq-uc.a.run.app/ws/live"


async def main() -> None:
    audio_config = None
    audio_chunks = 0
    turn_complete = False

    async with websockets.connect(URL, max_size=8_000_000) as ws:
        await ws.send(json.dumps({"type": "text", "text": "Say hello in one short sentence."}))

        for _ in range(200):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            t = msg.get("type")
            if t == "audio_config":
                audio_config = msg
            elif t == "audio" and msg.get("data_b64"):
                audio_chunks += 1
            elif t == "turn_complete":
                turn_complete = True
                break

    print("audio_config=", audio_config)
    print("audio_chunks=", audio_chunks)
    print("turn_complete=", turn_complete)


if __name__ == "__main__":
    asyncio.run(main())
