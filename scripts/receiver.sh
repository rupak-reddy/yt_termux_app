#!/data/data/com.termux/files/usr/bin/bash

URL=$(termux-share-get | grep -o 'https://[^ ]*')

if echo "$URL" | grep -q "youtu"; then
  ~/yt_termux_app/scripts/run.sh "$URL"
fi
