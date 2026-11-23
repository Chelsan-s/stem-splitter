#!/bin/zsh
# Starts the Stem Splitter server (if not running) and opens it in the browser.
PORT=8765
DIR="${0:A:h}"
if ! curl -s -o /dev/null "http://127.0.0.1:$PORT/api/songs"; then
  cd "$DIR"
  mkdir -p "$HOME/Music/StemSplitter"
  # Background QoS + lowest priority so separation never freezes the Mac.
  nohup taskpolicy -b nice -n 20 "$DIR/.venv/bin/uvicorn" app:app --host 127.0.0.1 --port $PORT \
    > "$HOME/Music/StemSplitter/server.log" 2>&1 &
  for i in {1..240}; do
    curl -s -o /dev/null "http://127.0.0.1:$PORT/api/songs" && break
    sleep 0.5
  done
fi
open "http://127.0.0.1:$PORT"
