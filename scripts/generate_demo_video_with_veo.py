#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Scene:
    title: str
    prompt: str


SCENES: list[Scene] = [
    Scene(
        title="Problem + Vision",
        prompt=(
            "Open with a futuristic command center. On-screen text: 'Teams need one agent that can listen, see, act, and create'. "
            "Cinematic camera dolly, high production value, realistic UI monitors."
        ),
    ),
    Scene(
        title="Live Voice Agent",
        prompt=(
            "A user speaks naturally to Aerivon. The system reacts in real-time with waveform activity and instant responses. "
            "Show interruption handling where user cuts in and the agent adapts mid-task."
        ),
    ),
    Scene(
        title="Planner + Reasoning",
        prompt=(
            "Visualize an agent planning board with steps appearing: Listening, Planning, Navigating, Analyzing, Creating, Rendering. "
            "Agent autonomously selects the next capability."
        ),
    ),
    Scene(
        title="UI Navigation",
        prompt=(
            "Agent navigates a retail website, reads the page visually, and extracts thematic signals from what it sees. "
            "Include browser motion and highlighted UI elements."
        ),
    ),
    Scene(
        title="Story Generation",
        prompt=(
            "From website observations, the agent creates a cyberpunk narrative. "
            "Show generated text flowing into illustrated frames with neon cinematic style."
        ),
    ),
    Scene(
        title="Multimodal Output",
        prompt=(
            "Demonstrate interleaved outputs: story text, generated illustration, narration waveform, and short cinematic video scene. "
            "The sequence must feel cohesive and real-time."
        ),
    ),
    Scene(
        title="Security + Reliability",
        prompt=(
            "Show secure guardrails dashboard: tool allowlist, argument validation, unsafe host blocking, rate control, and reconnect resilience. "
            "Convey trustworthiness and production readiness."
        ),
    ),
    Scene(
        title="Value Pitch",
        prompt=(
            "Final hero shot with clear value proposition text: 'Aerivon Live V2: one voice-driven multimodal operating system for exploration, creation, and execution'. "
            "End with strong cinematic logo reveal."
        ),
    ),
]


def _init_client() -> Any:
    from google import genai  # type: ignore
    from google.genai.types import HttpOptions  # type: ignore

    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").strip().lower() in {"1", "true", "yes"}
    project = (os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip()
    location = (os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1").strip()
    api_key = (
        os.getenv("GOOGLE_CLOUD_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or ""
    ).strip()

    http_options = HttpOptions(api_version="v1beta1")

    if use_vertex and project:
        return genai.Client(vertexai=True, project=project, location=location, http_options=http_options)

    if api_key:
        return genai.Client(api_key=api_key, http_options=http_options)

    raise RuntimeError(
        "Missing credentials. Set GOOGLE_GENAI_USE_VERTEXAI=true and GOOGLE_CLOUD_PROJECT (plus ADC), "
        "or set GEMINI_API_KEY/GOOGLE_API_KEY."
    )


def _extract_generated_videos(operation: Any) -> list[Any]:
    response = getattr(operation, "response", None)
    if response is None:
        return []

    for attr in ("generated_videos", "generatedVideos", "videos"):
        val = getattr(response, attr, None)
        if isinstance(val, list):
            return val

    if isinstance(response, dict):
        for key in ("generated_videos", "generatedVideos", "videos"):
            val = response.get(key)
            if isinstance(val, list):
                return val

    return []


def _download_video_reference(client: Any, video_ref: Any, out_path: Path) -> bool:
    candidates = [
        video_ref,
        getattr(video_ref, "video", None),
        getattr(video_ref, "file", None),
        getattr(video_ref, "video_file", None),
    ]

    for cand in candidates:
        if cand is None:
            continue

        if isinstance(cand, (bytes, bytearray)):
            out_path.write_bytes(bytes(cand))
            return True

        data = getattr(cand, "data", None)
        if isinstance(data, (bytes, bytearray)):
            out_path.write_bytes(bytes(data))
            return True

        # Current SDK shape for Veo responses: GeneratedVideo.video.video_bytes
        video_bytes = getattr(cand, "video_bytes", None)
        if isinstance(video_bytes, (bytes, bytearray)):
            out_path.write_bytes(bytes(video_bytes))
            return True

        files_api = getattr(client, "files", None)
        if files_api is not None and hasattr(files_api, "download"):
            try:
                downloaded = files_api.download(file=cand)
                if isinstance(downloaded, (bytes, bytearray)):
                    out_path.write_bytes(bytes(downloaded))
                    return True
                payload = getattr(downloaded, "data", None)
                if isinstance(payload, (bytes, bytearray)):
                    out_path.write_bytes(bytes(payload))
                    return True
            except Exception:
                pass

    return False


def _generate_scene_clip(
    client: Any,
    *,
    model: str,
    scene: Scene,
    scene_index: int,
    output_dir: Path,
    duration_seconds: int,
    aspect_ratio: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"scene_{scene_index:02d}.mp4"

    prompt = (
        "Create a polished product demonstration clip with natural motion, professional lighting, and no watermarks. "
        f"Scene title: {scene.title}. "
        f"Scene objective: {scene.prompt}"
    )

    models_api = getattr(client, "models", None)
    if models_api is None:
        raise RuntimeError("GenAI client has no models API.")

    request_config = {
        "duration_seconds": duration_seconds,
        "aspect_ratio": aspect_ratio,
    }

    operation = None
    if hasattr(models_api, "generate_videos"):
        operation = models_api.generate_videos(
            model=model,
            prompt=prompt,
            config=request_config,
        )
    elif hasattr(models_api, "generate_video"):
        operation = models_api.generate_video(
            model=model,
            prompt=prompt,
            config=request_config,
        )
    else:
        raise RuntimeError("Installed google-genai SDK does not expose generate_videos().")

    operations_api = getattr(client, "operations", None)
    if operations_api is not None and hasattr(operations_api, "get"):
        while not bool(getattr(operation, "done", False)):
            time.sleep(10)
            operation = operations_api.get(operation)

    generated = _extract_generated_videos(operation)
    if not generated:
        raise RuntimeError(f"No generated videos returned for scene {scene_index}: {scene.title}")

    if not _download_video_reference(client, generated[0], out_path):
        raise RuntimeError(
            "Video generation completed but download failed. "
            "Check SDK version and update download extraction logic."
        )

    return out_path


def _concat_clips_with_ffmpeg(clips: list[Path], output_path: Path, work_dir: Path) -> bool:
    if not clips:
        return False

    if shutil.which("ffmpeg") is None:
        return False

    concat_file = work_dir / "concat_list.txt"
    concat_file.write_text("\n".join([f"file '{p.resolve()}'" for p in clips]) + "\n", encoding="utf-8")

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False
    return output_path.exists()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a <4-minute Aerivon demo video with Veo.")
    parser.add_argument("--model", default=os.getenv("AERIVON_VIDEO_MODEL", "veo-3.0-generate-001"))
    parser.add_argument("--output-dir", default="demo_video_output")
    parser.add_argument("--duration-seconds", type=int, default=12)
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--max-scenes", type=int, default=len(SCENES))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.duration_seconds <= 0 or args.duration_seconds > 60:
        raise ValueError("--duration-seconds must be between 1 and 60.")

    selected_scenes = SCENES[: max(1, min(args.max_scenes, len(SCENES)))]
    total_duration = args.duration_seconds * len(selected_scenes)
    if total_duration >= 240:
        raise ValueError(
            f"Requested duration is {total_duration}s, must stay under 240s for <4-minute requirement."
        )

    output_dir = Path(args.output_dir)
    clips_dir = output_dir / "clips"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "model": args.model,
        "duration_seconds_per_scene": args.duration_seconds,
        "scene_count": len(selected_scenes),
        "total_seconds": total_duration,
        "scenes": [{"title": s.title, "prompt": s.prompt} for s in selected_scenes],
    }
    (output_dir / "demo_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if args.dry_run:
        print(f"Dry run complete. Manifest written to: {output_dir / 'demo_manifest.json'}")
        return 0

    client = _init_client()
    clips: list[Path] = []

    for index, scene in enumerate(selected_scenes, start=1):
        print(f"[{index}/{len(selected_scenes)}] Generating: {scene.title}")
        clip_path = _generate_scene_clip(
            client,
            model=args.model,
            scene=scene,
            scene_index=index,
            output_dir=clips_dir,
            duration_seconds=args.duration_seconds,
            aspect_ratio=args.aspect_ratio,
        )
        clips.append(clip_path)
        print(f"Saved: {clip_path}")

    final_path = output_dir / "Aerivon_Live_V2_Demo.mp4"
    if _concat_clips_with_ffmpeg(clips, final_path, output_dir):
        print(f"Final demo video: {final_path}")
    else:
        print("Could not concatenate clips automatically (ffmpeg missing or concat failed).")
        print("Individual clips are available in:", clips_dir)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
