# Unified Player

Lightweight Flask-based local video streamer with client-side players (Simple & Advanced). Streams local files or downloaded remote files (including zip extraction), supports on-the-fly reencoding with FFmpeg, basic hardware encoder selection, subtitle extraction, audio track selection and range requests.

---

## Table of Contents
- Overview
- Features
- Requirements
- Installation
- Usage
- Endpoints
- Frontend players (what they do)
- Configuration & notes
- Troubleshooting
- License

---

## Overview
This project hosts a small web service that:
- Downloads a remote file (or zip) to a local `downloads` folder.
- Lists available video files.
- Lets you play a selected file in either a Simple or Advanced web player.
- Streams video via raw byte-range requests or FFmpeg re-stream (transcode/packaging) on-demand.
- Extracts subtitle tracks to WebVTT via FFmpeg.

Designed for running on a local machine (Windows tested) and controlled via the browser UI.

---

## Features
- Download remote file URL (with progress UI).
- Auto-extract zip archives.
- File browser to pick playable files.
- Simple player: raw static streaming with Range support.
- Advanced player: FFmpeg-based streaming with:
  - Seekable start time
  - Audio track switching
  - Subtitle streaming (as WebVTT)
  - Quality selection (original/1080p/720p) with re-encoding
  - Hardware encoder selection (if FFmpeg supports it)
  - Client-side volume boost via Web Audio API
- Subtitle sync adjustments
- Basic process management to stop previous FFmpeg streams

---

## Requirements
- Python 3.8+
- FFmpeg (ffmpeg and ffprobe on PATH)
- Windows recommended (code uses WIN startup flags), but Linux/macOS should work with minor differences.
- Python packages:
  - Flask
  - requests
  - waitress

Suggested install command:
- Windows (PowerShell / CMD):
  - Install FFmpeg: choco install ffmpeg OR download from https://ffmpeg.org
  - Create venv and install python deps:
    ```
    python -m venv venv
    .\venv\Scripts\activate
    pip install flask requests waitress
    ```
- Or use pip:
  ```
  pip install flask requests waitress
  ```

---

## Installation
1. Clone or copy project to a folder (example shows where this README is placed).
2. Ensure `ffmpeg` and `ffprobe` are installed and available on PATH.
3. (Optional) Create and activate a virtual environment and pip install required packages.
4. Run the server:
   - From project directory:
     ```
     python main.py
     ```
   - The app uses Waitress and will bind to port `5500` by default.

Open: http://127.0.0.1:5500

---

## Usage

1. Open the landing page.
2. Paste a direct video URL (or a zip URL containing videos). Click "LOAD VIDEO".
   - The UI uploads the URL to `/process_url`, downloads and shows progress.
   - If a zip file, it's extracted to the `downloads` dir.
3. After download, you will be redirected to the file list (`/list_files`).
4. Choose a file and pick Simple or Advanced player.

CLI example to submit a URL (curl):
```
curl -X POST -F "url=https://example.com/video.mp4" http://127.0.0.1:5500/process_url
```

---

## Endpoints (summary)

- GET `/`  
  Landing page (progress + URL input).

- POST `/process_url`  
  Form field: `url` — downloads URL into `downloads/`. Unzips if archive.

- GET `/progress`  
  Returns JSON status of current download:
  `{ progress, status, msg, filename }`

- GET `/list_files`  
  Lists discovered video files in `downloads` with links to players.

- GET `/set_and_play?mode={simple|advanced}&path={abs_path}`  
  Sets current file and redirects to chosen player.

- GET `/play/simple`  
  Simple player UI. Uses `/raw_stream` for playback.

- GET `/play/advanced`  
  Advanced player UI. Accepts `audio_index` optional query.

- GET `/video_feed?start={seconds}&audio_index={index}&quality={original|1080p|720p}&hw={mode}`  
  FFmpeg-based streaming. Re-encodes or passes-through video depending on quality and codec.

- GET `/raw_stream`  
  Serves the file directly with support for HTTP Range requests. Use browser or clients that send Range headers.

- GET `/subtitle_feed?index={stream_index}&start={seconds}&offset={seconds}`  
  Uses FFmpeg to extract subtitle track and returns WebVTT (`text/vtt`). `offset` is used for sync adjustments.

- GET `/set_hw?mode={nvenc|qsv|amf|videotoolbox|cpu}`  
  Switch hardware encoding mode if available.

---

## Frontend players — quick notes

Simple player:
- Uses direct Range requests to serve file (`/raw_stream`).
- Basic playback UI, speed selector, basic volume.

Advanced player:
- Streams via `/video_feed` that runs FFmpeg and pipes an MP4 for smooth seeking/packaging.
- Supports selecting audio tracks, subtitle tracks, quality and hardware render mode.
- Provides subtitle sync adjustment and client-side volume boosting.

---

## Configuration & Important Code Notes
- DOWNLOAD_DIR is set near the top of `main.py` (`downloads`). Change if needed.
- FFmpeg is required to transcode, extract subtitles and probe metadata (`ffprobe`).
- Hardware encoder detection occurs at startup; if none found, CPU/libx264 used.
- The advanced streaming command uses fragmented MP4 (`-movflags frag_keyframe+empty_moov+default_base_moof`) to allow progressive playback from a pipe.
- `process_lock` and `active_processes` are used to ensure a single active FFmpeg subprocess per session id.
- The server binds to all interfaces `0.0.0.0` on port `5500` by default.

---

## Troubleshooting

- FFmpeg/ffprobe not found:
  - Ensure `ffmpeg` and `ffprobe` are on PATH. Confirm with `ffmpeg -version` and `ffprobe -version`.
- Download fails or progress stuck:
  - Check logs in console. Some servers block non-browser user-agents; server sets a browser UA header but remote host may still reject.
- No videos found after download:
  - If the downloaded file is a container not matching supported video extensions, move or rename into `downloads` or ensure zip contains supported files (`.mp4 .mkv .avi .mov .webm`).
- Subtitle extraction issues:
  - Some subtitle formats may not convert cleanly to WebVTT; check FFmpeg stderr in console for errors.
- Large files / memory:
  - Streaming is implemented to avoid loading full files into RAM; FFmpeg is streamed via pipe and raw files are read in chunks.
- Range header errors:
  - Some clients send non-standard Range formats. The server expects `bytes=<start>-<end>`.

---

## Security & Privacy
- This tool is intended for local/private use. Exposing it to public networks without proper hardening is risky.
- No auth is implemented. If exposing externally, add authentication, TLS and access control.
- Downloads are saved to `downloads/` and may be deleted or overwritten when new downloads are started (current code removes previous downloads on each new request).

---

## Extending / Development tips
- Add a small SPA or native Electron wrapper for a standalone app experience.
- Add authentication and HTTPS support.
- Persist file metadata rather than clearing downloads on each new download.
- Improve hardware detection logic (detect_hardware_encoders currently defaults to CPU).

---

## License
MIT-style permissive usage is assumed for personal/local projects. Check repository or author for licensing specifics.

---
