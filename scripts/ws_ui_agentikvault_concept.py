import asyncio
import json

import websockets

WS_URL = "wss://aerivon-live-agent-oauob6cvnq-uc.a.run.app/ws/ui"
TARGET_URL = "https://agentikvault.com"
TASK = (
    "Open agentikvault.com, extract key sections and visible headings, then create "
    "an illustrated cinematic video concept with 6 scenes."
)


async def main() -> None:
    statuses: list[str] = []
    action_results: list[dict] = []
    errors: list[str] = []
    done_note = ""

    async with websockets.connect(WS_URL, max_size=8_000_000) as ws:
        connected = json.loads(await ws.recv())
        print("connected=", connected)

        await ws.send(json.dumps({"type": "open", "url": TARGET_URL}))

        for _ in range(80):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=12.0))
            t = msg.get("type")
            if t == "status":
                s = str(msg.get("status") or "")
                statuses.append(s)
                if s == "ready":
                    break
            elif t == "error":
                errors.append(str(msg.get("error") or "unknown"))
                break

        await ws.send(json.dumps({"type": "task", "text": TASK}))

        for _ in range(260):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=15.0))
            t = msg.get("type")
            if t == "status":
                s = str(msg.get("status") or "")
                statuses.append(s)
                if s == "done":
                    done_note = str(msg.get("note") or "")
                    break
            elif t == "action_result":
                action_results.append(msg)
            elif t == "error":
                errors.append(str(msg.get("error") or "unknown"))
                break

    print("statuses=", statuses)
    print("action_results_count=", len(action_results))
    if action_results:
        print("last_action_result=", action_results[-1])
    print("done_note=", done_note)
    print("errors=", errors)


if __name__ == "__main__":
    asyncio.run(main())
