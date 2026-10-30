#!/usr/bin/env python3
"""Convert attributed short GIF clips into validated Telegram video stickers."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageSequence

HERE = Path(__file__).resolve().parent


def validate(path):
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ]))
    videos = [s for s in probe["streams"] if s["codec_type"] == "video"]
    assert len(videos) == 1 and len(probe["streams"]) == 1, "Must be silent video"
    stream = videos[0]
    assert stream["codec_name"] == "vp9"
    assert max(stream["width"], stream["height"]) == 512
    assert min(stream["width"], stream["height"]) > 0
    duration = float(probe["format"]["duration"])
    assert 0 < duration <= 3
    numerator, denominator = map(int, stream["r_frame_rate"].split("/"))
    assert 0 < numerator / denominator <= 30
    assert path.stat().st_size <= 256 * 1024
    hashes = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(path), "-f", "framemd5", "-"
    ], text=True)
    unique = {line.rsplit(",", 1)[-1].strip() for line in hashes.splitlines()
              if line and not line.startswith("#")}
    assert len(unique) >= 3, "A still image is not a moving sticker"
    return {"width": stream["width"], "height": stream["height"],
            "seconds": duration, "bytes": path.stat().st_size,
            "unique_frames": len(unique), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    manifest = json.loads((HERE / "manifest.json").read_text())
    source_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    report = {}
    for entry in manifest:
        target = HERE / entry["file"]
        if source_dir:
            source = source_dir / (target.stem + ".gif")
            image = Image.open(source)
            duration = sum(frame.info.get("duration", 100) for frame in ImageSequence.Iterator(image)) / 1000
            factor = min(1, 2.8 / duration)
            scale = "512:-2" if image.width >= image.height else "-2:512"
            for crf in (36, 40, 44, 48):
                subprocess.run([
                    "ffmpeg", "-v", "error", "-y", "-i", str(source), "-an",
                    "-vf", "setpts=%s*PTS,fps=20,scale=%s:flags=lanczos,setsar=1" % (factor, scale),
                    "-t", "2.95", "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p",
                    "-b:v", "0", "-crf", str(crf), "-row-mt", "1", "-deadline", "good",
                    "-cpu-used", "3", "-map_metadata", "-1", str(target)
                ], check=True)
                if target.stat().st_size <= 256 * 1024:
                    break
        report[entry["file"]] = validate(target)
        print(entry["file"], report[entry["file"]], flush=True)
    (HERE / "validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
