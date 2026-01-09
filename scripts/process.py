import sys, os, json, webvtt, yt_dlp, whisper, webbrowser

URL = sys.argv[1]
BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "data")
HTML = os.path.join(BASE, "..", "player.html")

os.makedirs(DATA, exist_ok=True)

# cleanup old files
for f in os.listdir(DATA):
    os.remove(os.path.join(DATA, f))

ydl_opts = {
    "outtmpl": f"{DATA}/video.%(ext)s",
    "format": "mp4",
    "writesubtitles": True,
    "writeautomaticsub": True,
    "subtitleslangs": ["en"],
    "ignoreerrors": True,
    "quiet": True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.extract_info(URL, download=True)

video = next(f for f in os.listdir(DATA) if f.endswith(".mp4"))
vtts = [f for f in os.listdir(DATA) if f.endswith(".vtt")]

captions = []

if vtts:
    vtt = webvtt.read(os.path.join(DATA, vtts[0]))
    for i, c in enumerate(vtt):
        captions.append({
            "id": i,
            "start": c.start_in_seconds,
            "end": c.end_in_seconds,
            "text": c.text.replace("\n", " ")
        })
else:
    model = whisper.load_model("tiny")
    result = model.transcribe(os.path.join(DATA, video))
    for i, s in enumerate(result["segments"]):
        captions.append({
            "id": i,
            "start": s["start"],
            "end": s["end"],
            "text": s["text"]
        })

with open(HTML, "w") as f:
    f.write(f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
.subs {{ height: 45vh; overflow-y: auto; }}
.sub {{ padding: 6px; }}
.active {{ background: #dbeafe; }}
</style>
</head>
<body>

<video id="v" controls width="100%">
  <source src="data/{video}" type="video/mp4">
</video>

<div class="subs" id="subs"></div>

<script>
const caps = {json.dumps(captions)};
const subs = document.getElementById("subs");
const v = document.getElementById("v");

caps.forEach(c => {{
  let d = document.createElement("div");
  d.className = "sub";
  d.id = "c"+c.id;
  d.innerText = `[${{c.start.toFixed(1)}}] ${{c.text}}`;
  d.onclick = () => v.currentTime = c.start;
  subs.appendChild(d);
}});

v.ontimeupdate = () => {{
  caps.forEach(c => {{
    let el = document.getElementById("c"+c.id);
    if (v.currentTime >= c.start && v.currentTime <= c.end) {{
      el.classList.add("active");
      el.scrollIntoView({{block:"center"}});
    }} else {{
      el.classList.remove("active");
    }}
  }});
}};
</script>
</body>
</html>
""")

webbrowser.open("file://" + HTML)
