import os
import subprocess
import json
import sys
import logging
import threading
import time
from flask import Flask, Response, request, render_template_string, redirect, url_for
from waitress import serve

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("WebPlayer")
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('waitress').setLevel(logging.ERROR)

app = Flask(__name__)
current_file_path = None
active_processes = {}
process_lock = threading.Lock()

# --- HARDWARE ACCELERATION STATE ---
# We store available modes here after detection
AVAILABLE_HW_MODES = {'cpu': 'CPU (Software)'} 
CURRENT_HW_MODE = 'cpu'

def detect_hardware_encoders():
    """Scans FFmpeg for available GPU encoders."""
    global AVAILABLE_HW_MODES, CURRENT_HW_MODE
    logger.info("Scanning for Hardware Acceleration...")
    
    try:
        # Hide console on Windows
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Run ffmpeg -encoders
        output = subprocess.check_output(['ffmpeg', '-v', 'error', '-encoders'], startupinfo=startupinfo).decode('utf-8')
        
        # Check specific encoders
        if 'h264_nvenc' in output:
            AVAILABLE_HW_MODES['nvenc'] = 'NVIDIA (NVENC)'
            CURRENT_HW_MODE = 'nvenc' # Auto-select if found
        if 'h264_qsv' in output:
            AVAILABLE_HW_MODES['qsv'] = 'Intel (QuickSync)'
            if CURRENT_HW_MODE == 'cpu': CURRENT_HW_MODE = 'qsv'
        if 'h264_videotoolbox' in output:
            AVAILABLE_HW_MODES['videotoolbox'] = 'Mac (VideoToolbox)'
            if CURRENT_HW_MODE == 'cpu': CURRENT_HW_MODE = 'videotoolbox'
        if 'h264_amf' in output:
            AVAILABLE_HW_MODES['amf'] = 'AMD (AMF)'
            if CURRENT_HW_MODE == 'cpu': CURRENT_HW_MODE = 'amf'

    except Exception as e:
        logger.warning(f"Could not detect encoders: {e}")
    
    logger.info(f"Available Modes: {list(AVAILABLE_HW_MODES.keys())}")
    logger.info(f"Defaulting to: {CURRENT_HW_MODE}")

# Run detection on startup
detect_hardware_encoders()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Python Cinema (Dynamic HW)</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #000; color: #fff; font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        header { background: #1f1f1f; padding: 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #00E676; position: fixed; top: 0; width: 100%; box-sizing: border-box; z-index: 20; transition: transform 0.5s ease-in-out; }
        .btn-file { background: #00E676; color: #000; border: none; padding: 8px 15px; font-weight: bold; cursor: pointer; border-radius: 4px; text-decoration: none; }
        .video-container { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #000; display: flex; justify-content: center; align-items: center; }
        video { width: 100%; height: 100%; object-fit: contain; }
        .loading-overlay { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 5; pointer-events: none; display: none; }
        .spinner { border: 8px solid rgba(255, 255, 255, 0.1); border-top: 8px solid #00E676; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .controls { background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.6) 60%, transparent 100%); padding: 20px 30px 30px 30px; display: flex; flex-direction: column; gap: 10px; position: fixed; bottom: 0; left: 0; width: 100%; box-sizing: border-box; z-index: 20; transition: opacity 0.5s ease-in-out; opacity: 1; }
        .ui-hidden header { transform: translateY(-100%); }
        .ui-hidden .controls { opacity: 0; pointer-events: none; }
        .ui-hidden { cursor: none; } 
        .seek-wrapper { display: flex; align-items: center; gap: 15px; margin-bottom: 5px; }
        input[type=range] { flex: 1; accent-color: #00E676; cursor: pointer; height: 6px; }
        
        /* Volume UI */
        .volume-wrapper { display: flex; align-items: center; gap: 8px; margin-left: 15px; background: rgba(255,255,255,0.1); padding: 5px 10px; border-radius: 20px; }
        .volume-wrapper i { width: 20px; text-align: center; font-size: 1.1rem; cursor: pointer; }
        #volumeBar { width: 80px; height: 4px; accent-color: #fff; }
        #volumeBar.boosted { accent-color: #ff3d00; }
        #volPercent { font-family: monospace; font-size: 0.8rem; min-width: 40px; text-align: center; }
        .vol-reset { font-size: 0.9rem; cursor: pointer; color: #aaa; margin-left: 5px; transition: color 0.2s;}
        .vol-reset:hover { color: #fff; }

        .time-display { font-family: monospace; font-size: 14px; min-width: 100px; text-align: right; user-select: none; }
        .buttons-row { display: flex; align-items: center; gap: 20px; }
        .btn-ctrl { background: none; border: none; color: white; font-size: 1.5rem; cursor: pointer; width: 35px; transition: color 0.2s; }
        .btn-ctrl:hover { color: #00E676; transform: scale(1.1); }
        .right-controls { margin-left: auto; display: flex; align-items: center; gap: 10px; }
        .select-group { display: flex; flex-direction: column; gap: 2px; }
        .select-group label { font-size: 0.7rem; color: #aaa; margin-left: 2px; }
        select { background: #333; color: white; border: 1px solid #555; padding: 5px; border-radius: 4px; cursor: pointer; max-width: 140px; font-size: 0.9rem;}
        .sync-msg { position: absolute; top: 10%; right: 5%; background: rgba(0,0,0,0.7); color: #fff; padding: 10px 20px; border-radius: 5px; font-weight: bold; display: none; pointer-events: none; z-index: 30; border: 1px solid #00E676; }
        .empty-state { text-align: center; color: #666; margin-top: 50px; }
    </style>
</head>
<body class="ui-visible">
    <header id="topBar"><h3>🚀 Python Cinema</h3><a href="/browse" class="btn-file">📂 Open File</a></header>
    <div class="video-container" id="mainContainer">
        {% if filename %}
            <div class="loading-overlay" id="loadingSpinner"><div class="spinner"></div></div>
            <div class="sync-msg" id="syncMsg">Subtitle Delay: 0ms</div>
            
            <video id="vid" autoplay onclick="togglePlay()" ondblclick="toggleFullScreen()" crossorigin="anonymous">
                <source id="vidSource" type="video/mp4">
            </video>

            <div class="controls" id="bottomBar">
                <div class="seek-wrapper"><span id="currentTime">00:00</span><input type="range" id="seekBar" min="0" max="{{ duration }}" value="0" step="1"><span id="totalTime">{{ duration_formatted }}</span></div>
                <div class="buttons-row">
                    <button class="btn-ctrl" onclick="togglePlay()"><i id="playIcon" class="fas fa-pause"></i></button>
                    <button class="btn-ctrl" onclick="seekRelative(-10)"><i class="fas fa-backward"></i></button>
                    <button class="btn-ctrl" onclick="seekRelative(10)"><i class="fas fa-forward"></i></button>
                    
                    <div class="volume-wrapper">
                        <i class="fas fa-volume-up" id="volIcon" onclick="toggleMute()"></i>
                        <input type="range" id="volumeBar" min="0" max="2" step="0.05" value="1" title="Volume (Up to 200%)">
                        <span id="volPercent">100%</span>
                        <i class="fas fa-undo vol-reset" onclick="resetVolume()" title="Reset to 100%"></i>
                    </div>

                    <div class="right-controls">
                        <div class="select-group"><label>Hardware</label>
                            <select id="hwSelect" onchange="changeHardware(this.value)">
                                {% for key, name in hw_modes.items() %}
                                    <option value="{{ key }}" {% if key == current_hw %}selected{% endif %}>{{ name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        
                        <div class="select-group"><label>Quality</label><select id="qualitySelect" onchange="changeQuality(this.value)"><option value="original" {% if current_quality == 'original' %}selected{% endif %}>Original</option><option value="1080p" {% if current_quality == '1080p' %}selected{% endif %}>1080p</option><option value="720p" {% if current_quality == '720p' %}selected{% endif %}>720p</option></select></div>
                        <div class="select-group"><label>Subtitles</label><select id="subSelect" onchange="changeSubtitleTrack(this.value)"><option value="-1">Off</option>{% for index, label in sub_tracks.items() %}<option value="{{ index }}">{{ label }}</option>{% endfor %}</select></div>
                        <div class="select-group"><label>Audio</label><select id="audioSelect" onchange="switchAudio(this.value)">{% for index, data in audio_tracks.items() %}<option value="{{ index }}" {% if index == current_audio %}selected{% endif %}>{{ data.label }}</option>{% endfor %}</select></div>
                        <button class="btn-ctrl" onclick="toggleFullScreen()"><i id="fsIcon" class="fas fa-expand"></i></button>
                    </div>
                </div>
            </div>
        {% else %}
            <div class="empty-state"><h1>No Movie Selected</h1><p>Click "Open File"</p></div>
        {% endif %}
    </div>
    <script>
        if (performance.getEntriesByType("navigation")[0].type === 'reload') window.location.href = "/reset";
        
        const video = document.getElementById('vid'); 
        const seekBar = document.getElementById('seekBar'); 
        const playIcon = document.getElementById('playIcon'); 
        const spinner = document.getElementById('loadingSpinner'); 
        const syncMsg = document.getElementById('syncMsg'); 
        const volumeBar = document.getElementById('volumeBar');
        const volIcon = document.getElementById('volIcon');
        const volPercent = document.getElementById('volPercent');
        const body = document.body;
        let hideTimer, syncTimer, seekTimeout;

        // --- AUDIO CONTEXT FOR BOOST ---
        let audioCtx, gainNode, source;
        function initAudioBoost() {
            if(!audioCtx) {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                audioCtx = new AudioContext();
                source = audioCtx.createMediaElementSource(video);
                gainNode = audioCtx.createGain();
                source.connect(gainNode);
                gainNode.connect(audioCtx.destination);
            }
        }

        if(volumeBar) {
            volumeBar.addEventListener('input', (e) => { applyVolume(parseFloat(e.target.value)); });
        }
        function applyVolume(val) {
            if(!audioCtx && val > 1) initAudioBoost();
            if (val <= 1) { video.volume = val; if(gainNode) gainNode.gain.value = 1; volumeBar.classList.remove('boosted'); } 
            else { video.volume = 1; initAudioBoost(); gainNode.gain.value = val; volumeBar.classList.add('boosted'); }
            volumeBar.value = val;
            volPercent.innerText = Math.round(val * 100) + '%';
            updateVolIcon(val);
        }
        function resetVolume() { applyVolume(1); }
        function updateVolIcon(val) {
            if(val == 0) volIcon.className = "fas fa-volume-mute";
            else if(val < 0.5) volIcon.className = "fas fa-volume-down";
            else if(val <= 1) volIcon.className = "fas fa-volume-up";
            else volIcon.className = "fas fa-bolt"; 
        }
        function toggleMute() {
            if(video.muted) { video.muted = false; applyVolume(video.getAttribute('data-last-vol') || 1); } 
            else { video.setAttribute('data-last-vol', volumeBar.value); video.muted = true; volumeBar.value = 0; volPercent.innerText = "0%"; updateVolIcon(0); }
        }

        function showLoading() { if(spinner) spinner.style.display = 'block'; }
        function hideLoading() { if(spinner) spinner.style.display = 'none'; }
        if (video) { video.addEventListener('waiting', showLoading); video.addEventListener('playing', hideLoading); video.addEventListener('seeking', showLoading); video.addEventListener('seeked', hideLoading); }

        let isSeeking = false; let totalDuration = {{ duration }}; 
        const startSeconds = {{ start_time }}; 
        let currentAudio = "{{ current_audio }}";
        let currentQuality = "{{ current_quality }}";
        let currentSubIndex = -1; let globalSubOffset = 0;
        let currentHw = "{{ current_hw }}";

        window.changeQuality = function(newQuality) { currentQuality = newQuality; reloadStream(); }
        window.switchAudio = function(newAudio) { currentAudio = newAudio; reloadStream(); }
        
        // NEW HW CHANGE LOGIC
        window.changeHardware = function(newHw) {
            // Need to update server state
            fetch(`/set_hw?mode=${newHw}`).then(() => {
                currentHw = newHw;
                reloadStream();
            });
        }

        function reloadStream() {
            let time = video.currentTime + (window.lastSeekTime || 0);
            window.lastSeekTime = time; 
            destroySubtitleTrack();
            showLoading();
            // Pass HW mode explicitly purely for clarity, though server has global state
            const url = `/video_feed?start=${time}&audio_index=${currentAudio}&quality=${currentQuality}&hw=${currentHw}`;
            video.src = url;
            video.play().catch(e => console.log(e));
            setTimeout(() => { refreshSubtitles(time); }, 200);
        }

        function destroySubtitleTrack() {
            const oldTrack = document.getElementById('dynamic-sub-track');
            if (oldTrack) oldTrack.remove(); 
            for(let i=0; i < video.textTracks.length; i++) video.textTracks[i].mode = 'disabled';
        }
        function changeSubtitleTrack(index) { currentSubIndex = index; globalSubOffset = 0; refreshSubtitles(window.lastSeekTime || 0); }
        function refreshSubtitles(startTime) { 
            destroySubtitleTrack(); if (currentSubIndex == -1) return; 
            const timestamp = Date.now();
            const trackUrl = `/subtitle_feed?index=${currentSubIndex}&start=${startTime}&offset=${globalSubOffset}&t=${timestamp}`;
            const newTrack = document.createElement('track'); newTrack.id = 'dynamic-sub-track'; newTrack.kind = 'subtitles'; newTrack.label = 'Dynamic Subs'; newTrack.srclang = 'en'; newTrack.default = true; newTrack.src = trackUrl;
            video.appendChild(newTrack); newTrack.onload = function() { this.track.mode = 'showing'; };
        }
        function adjustSync(amount) { 
            if (currentSubIndex == -1) return; globalSubOffset += amount; 
            syncMsg.innerText = `Subtitle Delay: ${Math.round(globalSubOffset * 1000)}ms`; syncMsg.style.display = 'block'; 
            clearTimeout(syncTimer); syncTimer = setTimeout(() => { syncMsg.style.display = 'none'; }, 2000); 
            refreshSubtitles(window.lastSeekTime + video.currentTime); 
        }

        if(seekBar) { 
            seekBar.addEventListener('input', (e) => { isSeeking = true; document.getElementById('currentTime').innerText = formatTime(e.target.value); }); 
            seekBar.addEventListener('change', (e) => { 
                let newTime = parseFloat(e.target.value); isSeeking = false; 
                clearTimeout(seekTimeout);
                seekTimeout = setTimeout(() => { window.lastSeekTime = newTime; reloadStream(); }, 200);
            }); 
        }

        if(video) { 
            window.lastSeekTime = startSeconds; 
            const url = `/video_feed?start=${startSeconds}&audio_index=${currentAudio}&quality=${currentQuality}&hw=${currentHw}`;
            video.src = url;
            showControls(); 
            setTimeout(() => { refreshSubtitles(startSeconds); }, 500);
        }

        setInterval(() => { if (video && !isSeeking && !video.paused) { let sessionTime = video.currentTime; let actualPosition = window.lastSeekTime + sessionTime; updateUI(actualPosition); } }, 250);
        function updateUI(seconds) { if(seconds > totalDuration) seconds = totalDuration; if(seekBar) seekBar.value = seconds; if(document.getElementById('currentTime')) document.getElementById('currentTime').innerText = formatTime(seconds); }
        function showControls() { body.classList.remove('ui-hidden'); clearTimeout(hideTimer); hideTimer = setTimeout(() => { if (video && !video.paused) body.classList.add('ui-hidden'); }, 5000); }
        document.addEventListener('mousemove', showControls); document.addEventListener('keydown', (e) => { if (!video) return; if(["Space","ArrowUp","ArrowDown","ArrowLeft","ArrowRight"].indexOf(e.code) > -1) e.preventDefault(); switch(e.code) { case 'Space': case 'k': togglePlay(); break; case 'ArrowRight': case 'l': seekRelative(10); break; case 'ArrowLeft': case 'j': seekRelative(-10); break; case 'KeyF': toggleFullScreen(); break; case 'KeyG': adjustSync(-0.05); break; case 'KeyH': adjustSync(0.05); break; } showControls(); });
        function togglePlay() { if (video.paused) { video.play(); playIcon.className = "fas fa-pause"; showControls(); } else { video.pause(); playIcon.className = "fas fa-play"; clearTimeout(hideTimer); body.classList.remove('ui-hidden'); } }
        function seekRelative(seconds) { let current = parseFloat(seekBar.value); let newTime = current + seconds; if(newTime < 0) newTime = 0; if(newTime > totalDuration) newTime = totalDuration; seekBar.value = newTime; seekBar.dispatchEvent(new Event('change')); showControls(); }
        function toggleFullScreen() { if (!document.fullscreenElement) document.documentElement.requestFullscreen(); else document.exitFullscreen(); }
        function formatTime(seconds) { let h = Math.floor(seconds / 3600); let m = Math.floor((seconds % 3600) / 60); let s = Math.floor(seconds % 60); if (h > 0) return `${h}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`; return `${m}:${s.toString().padStart(2,'0')}`; }
    </script>
</body>
</html>
"""

def get_media_info(filepath):
    logger.info(f"Analyzing: {filepath}")
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration", 
        "-show_entries", "stream=index,codec_type,codec_name,tags:stream_tags=language,title,handler_name",
        "-of", "json", filepath
    ]
    try:
        startupinfo = None
        if os.name == 'nt': startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        output = subprocess.check_output(cmd, startupinfo=startupinfo).decode("utf-8")
        data = json.loads(output)
        duration = float(data['format']['duration'])
        audio_tracks, sub_tracks = {}, {}
        has_video_h264 = False
        for stream in data.get('streams', []):
            idx = stream['index']
            codec = stream.get('codec_name', 'unknown')
            tags = stream.get('tags', {})
            title = tags.get('title', tags.get('handler_name'))
            lang = tags.get('language', 'und')
            if stream['codec_type'] == 'video' and codec == 'h264': has_video_h264 = True
            if title: label = f"{lang.upper()}: {title}"
            else: label = f"Track {idx} ({lang.upper()})"
            if stream['codec_type'] == 'audio': audio_tracks[str(idx)] = {'label': label, 'codec': codec}
            elif stream['codec_type'] == 'subtitle': sub_tracks[str(idx)] = label
        return audio_tracks, sub_tracks, duration, has_video_h264
    except Exception as e:
        logger.error(f"Metadata Error: {e}")
        return {}, {}, 0, False

def open_file_dialog_safe():
    script = "import tkinter as tk; from tkinter import filedialog; import os, sys; sys.stderr = open(os.devnull, 'w'); root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True); print(filedialog.askopenfilename(title='Select Movie'))"
    try:
        path = subprocess.check_output([sys.executable, "-c", script]).decode("utf-8").strip()
        return path if path else None
    except: return None

def format_seconds(seconds):
    m, s = divmod(seconds, 60); h, m = divmod(m, 60)
    if h > 0: return f"{int(h)}:{int(m):02d}:{int(s):02d}"
    return f"{int(m)}:{int(s):02d}"

@app.route('/reset')
def reset():
    global current_file_path
    current_file_path = None
    return redirect(url_for('index'))

@app.route('/set_hw')
def set_hw():
    global CURRENT_HW_MODE
    new_mode = request.args.get('mode')
    if new_mode in AVAILABLE_HW_MODES:
        CURRENT_HW_MODE = new_mode
        logger.info(f"Switched Hardware Engine to: {AVAILABLE_HW_MODES[new_mode]}")
        return "OK"
    return "Invalid", 400

@app.route('/')
def index():
    global current_file_path
    start_time_arg = request.args.get('t', 0)
    audio_tracks, sub_tracks = {}, {}
    duration = 0
    current_audio = "1"
    current_quality = "original"
    if current_file_path:
        audio_tracks, sub_tracks, duration, _ = get_media_info(current_file_path)
        current_audio = request.args.get('audio_index')
        if not current_audio and audio_tracks: current_audio = list(audio_tracks.keys())[0]
    return render_template_string(
        HTML_TEMPLATE, filename=os.path.basename(current_file_path) if current_file_path else None,
        audio_tracks=audio_tracks, sub_tracks=sub_tracks, current_audio=current_audio,
        current_quality=current_quality, duration=duration, duration_formatted=format_seconds(duration),
        start_time=start_time_arg,
        # Pass HW options to frontend
        hw_modes=AVAILABLE_HW_MODES, current_hw=CURRENT_HW_MODE
    )

@app.route('/browse')
def browse():
    global current_file_path
    selected = open_file_dialog_safe()
    if selected: current_file_path = selected
    return redirect(url_for('index'))

def get_video_codec_flags(quality, is_h264_source):
    # Smart Remux (Direct Copy if compatible)
    if quality == 'original' and is_h264_source: 
        return ['-c:v', 'copy']
    
    # Use the Dynamic Global Setting
    mode = CURRENT_HW_MODE 
    
    base = []
    
    # --- NVIDIA (NVENC) CONFIGURATION ---
    if mode == 'nvenc': 
        base = [
            '-c:v', 'h264_nvenc',       # Use NVIDIA Encoder
            '-pix_fmt', 'yuv420p',      # MANDATORY: Browser colors
            '-preset', 'p2',            # Performance preset
            '-profile:v', 'high',       # MANDATORY: Standard Profile for players
            '-b:v', '5M',               # Target Bitrate (5Mbps)
            '-bufsize', '10M'           # Buffer size
        ]
    
    # --- INTEL (QUICKSYNC) ---
    elif mode == 'qsv': 
        base = ['-c:v', 'h264_qsv', '-preset', 'veryfast', '-pix_fmt', 'yuv420p']
        
    # --- MAC (VIDEOTOOLBOX) ---
    elif mode == 'videotoolbox': 
        base = ['-c:v', 'h264_videotoolbox', '-realtime', 'true', '-pix_fmt', 'yuv420p']
        
    # --- AMD (AMF) ---
    elif mode == 'amf': 
        base = ['-c:v', 'h264_amf', '-usage', 'lowlatency', '-pix_fmt', 'yuv420p']
        
    # --- CPU (SOFTWARE) ---
    else: 
        base = ['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-threads', '0', '-pix_fmt', 'yuv420p']
    
    # Scale if needed
    if quality == '1080p': base.extend(['-vf', 'scale=-2:1080'])
    elif quality == '720p': base.extend(['-vf', 'scale=-2:720'])
    
    return base

@app.route('/subtitle_feed')
def subtitle_feed():
    sub_index = request.args.get('index')
    start_time = float(request.args.get('start', '0'))
    offset = float(request.args.get('offset', '0'))
    if not current_file_path or not sub_index: return "Error", 400
    adjusted = max(0, start_time - offset)
    cmd = ['ffmpeg', '-ss', str(adjusted), '-i', current_file_path, '-map', f'0:{sub_index}', '-vn', '-an', '-f', 'webvtt', '-loglevel', 'error', 'pipe:1']
    try:
        startupinfo = None
        if os.name == 'nt': startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, startupinfo=startupinfo)
        out, _ = proc.communicate()
        return Response(out, mimetype='text/vtt')
    except: return "Error", 500

@app.route('/video_feed')
def video_feed():
    global current_file_path
    if not current_file_path: return "No file", 404
    audio_index = request.args.get('audio_index', '1')
    start_time = request.args.get('start', '0')
    quality = request.args.get('quality', 'original')
    session_id = 'video_stream'

    with process_lock:
        if session_id in active_processes:
            try: active_processes[session_id].kill()
            except: pass

    audio_tracks, _, _, is_h264 = get_media_info(current_file_path)
    audio_codec = audio_tracks.get(audio_index, {}).get('codec', 'unknown')
    
    # Input Flags
    input_flags = ['-ss', str(start_time)]
    
    cmd = ['ffmpeg'] + input_flags + ['-i', current_file_path, '-map', '0:v:0', '-map', f'0:{audio_index}']
    
    # Get Hardware Flags
    cmd.extend(get_video_codec_flags(quality, is_h264))
    
    # --- AUDIO FIX: ALWAYS TRANSCODE TO STEREO ---
    # Browsers often fail with 5.1 surround sound pass-through. 
    # We force 2 channels (Stereo) AAC.
    cmd.extend(['-c:a', 'aac', '-ac', '2', '-b:a', '192k'])
    
    # Web Container Flags
    cmd.extend(['-f', 'mp4', '-movflags', 'frag_keyframe+empty_moov+default_base_moof', '-loglevel', 'warning', 'pipe:1'])

    print(f"Executing: {' '.join(cmd)}") 

    startupinfo = None
    if os.name == 'nt': 
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    def generate():
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=sys.stderr, bufsize=65536, startupinfo=startupinfo)
        with process_lock: active_processes[session_id] = process
        try:
            while True:
                data = process.stdout.read(65536)
                if not data: break
                yield data
        except Exception as e:
            logger.error(f"Stream Error: {e}")
        finally:
            process.kill()

    return Response(generate(), mimetype='video/mp4')

if __name__ == '__main__':
    print("---------------------------------------")
    print(" 🚀 HARDWARE SELECTOR ADDED")
    print(f" Available Modes: {list(AVAILABLE_HW_MODES.keys())}")
    print(" Go to: http://127.0.0.1:5500")
    print("---------------------------------------")
    serve(app, host='0.0.0.0', port=5500, threads=6)