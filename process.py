#!/usr/bin/env python3
# process.py
# Usage: python process.py "https://www.youtube.com/watch?v=VIDEO_ID"

import sys
import os
import json
import subprocess
import yt_dlp
import webvtt

# Whisper is optional on Android - see notes below
try:
    import whisper
    WHISPER_AVAILABLE = True
except Exception:
    WHISPER_AVAILABLE = False

def error_exit(msg):
    print("ERROR:", msg)
    sys.exit(1)

if len(sys.argv) < 2:
    error_exit("Missing YouTube URL. Usage: python process.py \"<YOUTUBE_URL>\"")

URL = sys.argv[1].strip()
BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
HTML_FILE = os.path.join(BASE, "player.html")

os.makedirs(DATA, exist_ok=True)

# Remove previous files in data folder (keeps only one video at a time)
for f in os.listdir(DATA):
    try:
        os.remove(os.path.join(DATA, f))
    except Exception:
        pass

# yt-dlp options
ydl_opts = {
    "outtmpl": os.path.join(DATA, "video.%(ext)s"),
    "format": "mp4",
    "writesubtitles": True,
    "writeautomaticsub": True,
    "subtitleslangs": ["en"],
    "subtitlesformat": "vtt",
    "ignoreerrors": True,
    "quiet": True,
}

print("Downloading video and captions (if available)...")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        ydl.extract_info(URL, download=True)
    except Exception as e:
        print("yt-dlp warning/error:", e)

# Find downloaded video file
video_file = None
vtt_files = []
for f in os.listdir(DATA):
    if f.endswith(".mp4"):
        video_file = f
    if f.endswith(".vtt"):
        vtt_files.append(f)

if video_file is None:
    error_exit("No video file was downloaded. Check the URL and network.")

captions = []

# If VTT subtitles exist, parse them
if len(vtt_files) > 0:
    print("Found VTT subtitles, parsing...")
    # prefer first VTT file; if multiple, you can pick logic here
    vtt_path = os.path.join(DATA, vtt_files[0])
    try:
        for i, caption in enumerate(webvtt.read(vtt_path)):
            captions.append({
                "id": i,
                "start": caption.start_in_seconds,
                "end": caption.end_in_seconds,
                "text": caption.text.replace("\n", " ")
            })
    except Exception as e:
        print("Failed to parse VTT:", e)
        captions = []
else:
    # Fallback to Whisper if available
    if WHISPER_AVAILABLE:
        print("No VTT subtitles found. Running Whisper (fallback)...")
        model = whisper.load_model("tiny")  # tiny is fastest & smallest
        audio_path = os.path.join(DATA, video_file)
        try:
            res = model.transcribe(audio_path)
            for i, seg in enumerate(res.get("segments", [])):
                captions.append({
                    "id": i,
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                })
        except Exception as e:
            print("Whisper error:", e)
    else:
        print("No VTT subtitles and Whisper is not available. Nothing to show as captions.")

# Build HTML player (video + subtitle list)
print("Writing player HTML...")
player_html = f"""<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Video Player</title>
<style>
body {{ font-family: system-ui, Arial, sans-serif; margin:0; padding:0; }}
#video {{ width: 100%; max-height: 55vh; background: black; }}
.subs {{ height: 45vh; overflow-y: auto; padding: 6px; box-sizing: border-box; }}
.sub {{ padding: 8px; border-bottom: 1px solid #eee; }}
.active {{ background: #e6f2ff; }}
.time {{ color: #666; font-size: 0.85em; margin-right:6px; }}
</style>
</head>
<body>

<video id="video" controls>
  <source src="data/{video_file}" type="video/mp4">
  Your browser does not support HTML5 video.
</video>

<div class="subs" id="subs"></div>

<script>
const captions = {json.dumps(captions)};
const subs = document.getElementById('subs');
const video = document.getElementById('video');

function fmt(n) {{
  return (Math.floor(n/60) + ':' + ('0' + Math.floor(n%60)).slice(-2));
}}

captions.forEach(c => {{
  const d = document.createElement('div');
  d.className = 'sub';
  d.id = 'c' + c.id;
  const t = document.createElement('span');
  t.className = 'time';
  t.textContent = '[' + fmt(c.start) + ']';
  d.appendChild(t);
  d.appendChild(document.createTextNode(c.text));
  d.onclick = () => video.currentTime = c.start + 0.01;
  subs.appendChild(d);
}});

video.ontimeupdate = () => {{
  const t = video.currentTime;
  captions.forEach(c => {{
    const el = document.getElementById('c' + c.id);
    if (!el) return;
    if (t >= c.start && t <= c.end) {{
      if (!el.classList.contains('active')) {{
        el.classList.add('active');
        el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
      }}
    }} else {{
      el.classList.remove('active');
    }}
  }});
}};
</script>

</body>
</html>
"""

with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(player_html)

print("Player written to:", HTML_FILE)
# Try opening the file on Android using termux-open if available
try:
    subprocess.run(["termux-open", HTML_FILE])
except Exception:
    print("Could not auto-open. Please open the file manually on the phone:", HTML_FILE)

print("Done.")
