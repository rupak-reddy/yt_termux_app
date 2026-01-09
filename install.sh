#!/data/data/com.termux/files/usr/bin/bash

pkg update -y
pkg install -y python ffmpeg git nodejs termux-api
pip install --upgrade pip
pip install yt-dlp webvtt-py openai-whisper torch

chmod +x scripts/*.sh

echo "Setup complete."
