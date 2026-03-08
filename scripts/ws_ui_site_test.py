import asyncio
import json

import websockets

WS_URL = "wss://aerivon-live-agent-oauob6cvnq-uc.a.run.app/ws/ui"
TARGET_URL = "https://agentikvault.com"
TASK = "Analyze this website and extract: 1) the site title, 2) what the product/service appears to be, and 3) two visible navigation/menu labels."


async def main() -> None:
    statuses: list[str] = []
    actions: list[dict] = []
    screenshots = 0
    done_note = ""
    errors: list[str] = []

    async with websockets.connect(WS_URL, max_size=8_000_000) as ws:
        first = json.loads(await ws.recv())
        print("connected_msg=", first)

        await ws.send(json.dumps({"type": "open", "url": TARGET_URL}))

        ready = False
        for _ in range(80):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10.0))
            t = msg.get("type")
            if t == "status":
                s = str(msg.get("status") or "")
                statuses.append(s)
                if s == "ready":
                    ready = True
                    break
            elif t == "error":
                errors.append(str(msg.get("error") or "unknown"))
                break
            elif t == "screenshot":
                screenshots += 1

        if not ready:
            print("statuses=", statuses)
            print("errors=", errors)
            return

        await ws.send(json.dumps({"type": "task", "text": TASK}))

        for _ in range(220):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=12.0))
            t = msg.get("type")
            if t == "status":
                s = str(msg.get("status") or "")
                statuses.append(s)
                if s == "done":
                    done_note = str(msg.get("note") or "")
                    break
            elif t == "action_result":
                actions.append(msg)
            elif t == "screenshot":
                screenshots += 1
            elif t == "error":
                errors.append(str(msg.get("error") or "unknown"))
                break

    print("statuses=", statuses)
    print("screenshots=", screenshots)
    print("action_results=", len(actions))
    if actions:
        print("last_action_result=", actions[-1])
    print("done_note=", done_note)
    print("errors=", errors)


if __name__ == "__main__":
    asyncio.run(main())
