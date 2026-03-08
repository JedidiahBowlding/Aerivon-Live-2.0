import json
import time
import urllib.request
from pathlib import Path

BASE = "https://aerivon-live-agent-oauob6cvnq-uc.a.run.app"
PROMPT = (
    "Create a 30-second illustrated cinematic product video SPECIFICALLY for Agentik Vault "
    "(agentikvault.com). HARD CONSTRAINTS: Do NOT show ocean, beach, sunrise, water, waves, "
    "or nature scenery. Do NOT use abstract stock footage. Ground every frame in this website "
    "context and its visible content: title 'Agentik Vault - AI Agent Provisioning Platform', "
    "CTA 'Connect Wallet', phrase 'YOUR PRIVATE AI GATEWAY', features 'Multi-Channel Gateway', "
    "'AI Coding Agent', 'Self-Hosted & Private', 'Full Control Dashboard', 'Rich Media Support', "
    "'Pay with SOL', and onboarding flow 'Subscribe with SOL -> Get Your Private Instance -> "
    "Connect Your Apps'. Show futuristic dashboard UI, wallet connection, multi-channel message "
    "nodes (WhatsApp/Telegram/Discord/iMessage), tool streaming, memory timeline, and secure "
    "vault motifs. Include on-screen branded text snippets from the site. Cinematic style: "
    "cyber-noir, neon accents, volumetric light, smooth dolly and match-cut transitions. End "
    "card: 'Agentik Vault - One gateway. Infinite possibilities.'"
)


def http_json(url: str, payload: dict | None = None) -> dict:
    if payload is None:
        req = urllib.request.Request(url, method="GET")
    else:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url: str, out_path: Path) -> int:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = resp.read()
    out_path.write_bytes(data)
    return len(data)


def main() -> int:
    create = http_json(
        f"{BASE}/veo/jobs",
        {
            "prompt": PROMPT,
            "duration_seconds": 30,
            "aspect_ratio": "16:9",
            "model": "veo-3.1-generate-001",
        },
    )
    print("created=", create)
    job_id = str(create.get("job_id") or "").strip()
    if not job_id:
        print("failed_to_parse_job_id")
        return 1

    final = create
    for i in range(1, 240):
        status = http_json(f"{BASE}/veo/jobs/{job_id}")
        final = status
        print(f"poll_{i} status={status.get('status')} progress={status.get('progress')}")
        if status.get("status") in {"completed", "failed"}:
            break
        time.sleep(8)

    print("final=", final)
    if final.get("status") != "completed":
        return 2

    video_url = str(final.get("video_url") or "").strip()
    if not video_url:
        print("missing_video_url")
        return 3

    if video_url.startswith("http://") or video_url.startswith("https://"):
        full_url = video_url
    else:
        full_url = f"{BASE}{video_url if video_url.startswith('/') else '/' + video_url}"

    out_path = Path("/tmp/agentikvault_site_grounded_30s_test.mp4")
    size = download_file(full_url, out_path)
    print(f"downloaded={out_path} bytes={size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
