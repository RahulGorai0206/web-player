import os
import subprocess
import json
import sys
import logging
import threading
import time
import requests
import zipfile
import shutil
import re
import mimetypes
from flask import Flask, Response, request, render_template_string, redirect, url_for, send_file, jsonify
from waitress import serve

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("WebPlayer")
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('waitress').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

app = Flask(__name__)
current_file_path = None
active_processes = {}
process_lock = threading.Lock()
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- GLOBAL PROGRESS STATE ---
# We use this to track download status across threads
download_state = {
    'progress': 0,
    'status': 'Idle',
    'msg': 'Waiting...',
    'filename': ''
}

# --- HARDWARE ACCELERATION STATE ---
AVAILABLE_HW_MODES = {'cpu': 'CPU (Software)'} 
CURRENT_HW_MODE = 'cpu'

def detect_hardware_encoders():
    """Scans FFmpeg for available GPU encoders."""
    global AVAILABLE_HW_MODES, CURRENT_HW_MODE
    logger.info("Scanning for Hardware Acceleration...")
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        output = subprocess.check_output(['ffmpeg', '-v', 'error', '-encoders'], startupinfo=startupinfo).decode('utf-8')
        
        if 'h264_nvenc' in output:
            AVAILABLE_HW_MODES['nvenc'] = 'NVIDIA (NVENC)'
            CURRENT_HW_MODE = 'nvenc' 
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
    CURRENT_HW_MODE = 'cpu'
    logger.info(f"Defaulting to: {CURRENT_HW_MODE}")

detect_hardware_encoders()

# ==========================================
# TEMPLATES
# ==========================================

# 1. LANDING PAGE (With Progress Bar)
LANDING_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Python Cinema - Loader</title>
    <style>
        body { background: #000; color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: #1f1f1f; padding: 40px; border-radius: 8px; border: 1px solid #333; width: 500px; text-align: center; }
        h1 { color: #00E676; margin-bottom: 20px; }
        input { width: 90%; padding: 12px; margin-bottom: 20px; background: #333; border: 1px solid #555; color: white; border-radius: 4px; font-size: 1rem; }
        button { background: #00E676; color: #000; border: none; padding: 12px 30px; font-weight: bold; cursor: pointer; border-radius: 4px; font-size: 1rem; width: 100%; transition: 0.2s; }
        button:hover { opacity: 0.9; }
        
        /* Progress UI */
        #progressArea { display: none; margin-top: 25px; }
        .progress-track { background: #333; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 10px; }
        .progress-fill { background: #00E676; height: 100%; width: 0%; transition: width 0.3s ease; }
        .status-text { color: #aaa; font-size: 0.9rem; margin-bottom: 5px; display: flex; justify-content: space-between; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Python Cinema</h1>
        <p>Enter Video URL or Zip URL</p>
        
        <form id="dlForm">
            <input type="text" id="urlInput" name="url" placeholder="https://example.com/movie.mp4" required autocomplete="off">
            <button type="submit" id="dlBtn">LOAD CONTENT</button>
        </form>

        <div id="progressArea">
            <div class="status-text">
                <span id="statusMsg">Starting...</span>
                <span id="percentTxt">0%</span>
            </div>
            <div class="progress-track">
                <div class="progress-fill" id="pBar"></div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('dlForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const url = document.getElementById('urlInput').value;
            const btn = document.getElementById('dlBtn');
            const progressArea = document.getElementById('progressArea');
            
            // UI Updates
            btn.style.display = 'none';
            progressArea.style.display = 'block';

            // Start Download AJAX
            const formData = new FormData();
            formData.append('url', url);

            fetch('/process_url', { method: 'POST', body: formData })
                .then(response => response.json())
                .then(data => {
                    if(data.status === 'ok') {
                        window.location.href = '/list_files';
                    } else {
                        alert("Error: " + data.message);
                        location.reload();
                    }
                })
                .catch(err => {
                    alert("Network Error: " + err);
                    location.reload();
                });

            // Start Polling Progress
            const pollInterval = setInterval(() => {
                fetch('/progress')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('pBar').style.width = data.progress + '%';
                        document.getElementById('percentTxt').innerText = data.progress + '%';
                        document.getElementById('statusMsg').innerText = data.msg;
                        
                        if (data.status === 'Done') {
                            clearInterval(pollInterval);
                            document.getElementById('statusMsg').innerText = "Complete! Redirecting...";
                        }
                    });
            }, 500);
        });
    </script>
</body>
</html>
"""

# 2. FILE SELECTION
SELECTION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Select Content</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #000; color: #fff; font-family: 'Segoe UI', sans-serif; padding: 50px; }
        .file-card { background: #1f1f1f; padding: 20px; margin-bottom: 15px; border-left: 4px solid #00E676; display: flex; justify-content: space-between; align-items: center; border-radius: 4px; }
        .name { font-weight: bold; font-size: 1.1rem; }
        .btn { padding: 8px 15px; border-radius: 4px; text-decoration: none; font-weight: bold; margin-left: 10px; border: none; cursor: pointer; display: inline-block; }
        .btn-adv { background: #00E676; color: #000; }
        .btn-simple { background: #333; color: #fff; border: 1px solid #555; }
        .btn:hover { opacity: 0.8; }
        h2 { border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h2>📂 Available Media</h2>
    {% for file in files %}
    <div class="file-card">
        <div class="name"><i class="fas fa-film"></i> {{ file.name }}</div>
        <div>
            <a href="/set_and_play?mode=simple&path={{ file.path }}" class="btn btn-simple">⚡ Simple Player</a>
            <a href="/set_and_play?mode=advanced&path={{ file.path }}" class="btn btn-adv">🚀 Advanced Player</a>
        </div>
    </div>
    {% endfor %}
    <br>
    <a href="/" style="color: #666; text-decoration: none;">&larr; Load different URL</a>
</body>
</html>
"""

# 3. ADVANCED PLAYER
ADVANCED_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Python Cinema (Advanced)</title>
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
    </style>
</head>
<body class="ui-visible">
    <header id="topBar"><h3>🚀 Advanced Cinema</h3><a href="/list_files" class="btn-file">📂 Menu</a></header>
    <div class="video-container" id="mainContainer">
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
    </div>
    <script>
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
        if(volumeBar) { volumeBar.addEventListener('input', (e) => { applyVolume(parseFloat(e.target.value)); }); }
        function applyVolume(val) {
            if(!audioCtx && val > 1) initAudioBoost();
            if (val <= 1) { video.volume = val; if(gainNode) gainNode.gain.value = 1; volumeBar.classList.remove('boosted'); } 
            else { video.volume = 1; initAudioBoost(); gainNode.gain.value = val; volumeBar.classList.add('boosted'); }
            volumeBar.value = val; volPercent.innerText = Math.round(val * 100) + '%'; updateVolIcon(val);
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
        window.changeHardware = function(newHw) { fetch(`/set_hw?mode=${newHw}`).then(() => { currentHw = newHw; reloadStream(); }); }

        function reloadStream() {
            let time = video.currentTime + (window.lastSeekTime || 0);
            window.lastSeekTime = time; 
            destroySubtitleTrack(); showLoading();
            const url = `/video_feed?start=${time}&audio_index=${currentAudio}&quality=${currentQuality}&hw=${currentHw}`;
            video.src = url; video.play().catch(e => console.log(e));
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
            video.src = url; showControls(); 
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

# 4. SIMPLE PLAYER
SIMPLE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Python Cinema (Simple)</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        /* Exact copy of Advanced CSS */
        body { background: #000; color: #fff; font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        header { background: #1f1f1f; padding: 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #00E676; position: fixed; top: 0; width: 100%; box-sizing: border-box; z-index: 20; transition: transform 0.5s ease-in-out; }
        .btn-file { background: #333; color: #fff; border: 1px solid #555; padding: 8px 15px; font-weight: bold; cursor: pointer; border-radius: 4px; text-decoration: none; }
        .video-container { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #000; display: flex; justify-content: center; align-items: center; }
        video { width: 100%; height: 100%; object-fit: contain; }
        .controls { background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.6) 60%, transparent 100%); padding: 20px 30px 30px 30px; display: flex; flex-direction: column; gap: 10px; position: fixed; bottom: 0; left: 0; width: 100%; box-sizing: border-box; z-index: 20; transition: opacity 0.5s ease-in-out; opacity: 1; }
        .ui-hidden header { transform: translateY(-100%); }
        .ui-hidden .controls { opacity: 0; pointer-events: none; }
        .ui-hidden { cursor: none; } 
        .seek-wrapper { display: flex; align-items: center; gap: 15px; margin-bottom: 5px; }
        input[type=range] { flex: 1; accent-color: #00E676; cursor: pointer; height: 6px; }
        .volume-wrapper { display: flex; align-items: center; gap: 8px; margin-left: 15px; background: rgba(255,255,255,0.1); padding: 5px 10px; border-radius: 20px; }
        .volume-wrapper i { width: 20px; text-align: center; font-size: 1.1rem; cursor: pointer; }
        #volumeBar { width: 80px; height: 4px; accent-color: #fff; }
        #volumeBar.boosted { accent-color: #ff3d00; }
        #volPercent { font-family: monospace; font-size: 0.8rem; min-width: 40px; text-align: center; }
        .buttons-row { display: flex; align-items: center; gap: 20px; }
        .btn-ctrl { background: none; border: none; color: white; font-size: 1.5rem; cursor: pointer; width: 35px; transition: color 0.2s; }
        .btn-ctrl:hover { color: #00E676; transform: scale(1.1); }
        .right-controls { margin-left: auto; display: flex; align-items: center; gap: 10px; }
        .select-group { display: flex; flex-direction: column; gap: 2px; }
        .select-group label { font-size: 0.7rem; color: #aaa; margin-left: 2px; }
        select { background: #333; color: white; border: 1px solid #555; padding: 5px; border-radius: 4px; cursor: pointer; max-width: 140px; font-size: 0.9rem;}
        .loading-overlay { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 5; pointer-events: none; display: none; }
        .spinner { border: 8px solid rgba(255, 255, 255, 0.1); border-top: 8px solid #00E676; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .time-display { font-family: monospace; font-size: 14px; min-width: 100px; text-align: right; user-select: none; }
    </style>
</head>
<body class="ui-visible">
    <header id="topBar"><h3>⚡ Simple Cinema</h3><a href="/list_files" class="btn-file">📂 Menu</a></header>
    <div class="video-container" id="mainContainer">
        <div class="loading-overlay" id="loadingSpinner"><div class="spinner"></div></div>
        
        <video id="vid" autoplay onclick="togglePlay()" ondblclick="toggleFullScreen()">
            <source src="/raw_stream" type="video/mp4">
        </video>

        <div class="controls" id="bottomBar">
            <div class="seek-wrapper">
                <span id="currentTime" class="time-display" style="text-align:left; min-width:auto;">00:00</span>
                <input type="range" id="seekBar" min="0" value="0" step="1">
                <span id="totalTime" class="time-display">{{ duration_formatted }}</span>
            </div>
            <div class="buttons-row">
                <button class="btn-ctrl" onclick="togglePlay()"><i id="playIcon" class="fas fa-pause"></i></button>
                <button class="btn-ctrl" onclick="seekRelative(-10)"><i class="fas fa-backward"></i></button>
                <button class="btn-ctrl" onclick="seekRelative(10)"><i class="fas fa-forward"></i></button>
                
                <div class="volume-wrapper">
                    <i class="fas fa-volume-up" id="volIcon" onclick="toggleMute()"></i>
                    <input type="range" id="volumeBar" min="0" max="2" step="0.05" value="1" title="Volume (Up to 200%)">
                    <span id="volPercent">100%</span>
                </div>

                <div class="right-controls">
                    <div class="select-group"><label>Speed</label>
                        <select onchange="document.getElementById('vid').playbackRate = this.value">
                            <option value="0.5">0.5x</option><option value="1" selected>1.0x</option>
                            <option value="1.5">1.5x</option><option value="2">2.0x</option>
                        </select>
                    </div>
                    <button class="btn-ctrl" onclick="toggleFullScreen()"><i id="fsIcon" class="fas fa-expand"></i></button>
                </div>
            </div>
        </div>
    </div>
    <script>
        const video = document.getElementById('vid');
        const seekBar = document.getElementById('seekBar');
        const playIcon = document.getElementById('playIcon');
        const spinner = document.getElementById('loadingSpinner');
        const volumeBar = document.getElementById('volumeBar');
        const volIcon = document.getElementById('volIcon');
        const volPercent = document.getElementById('volPercent');
        const body = document.body;
        let hideTimer;

        // --- AUDIO BOOST (Client Side) ---
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
        volumeBar.addEventListener('input', (e) => { applyVolume(parseFloat(e.target.value)); });
        function applyVolume(val) {
            if(!audioCtx && val > 1) initAudioBoost();
            if (val <= 1) { video.volume = val; if(gainNode) gainNode.gain.value = 1; volumeBar.classList.remove('boosted'); } 
            else { video.volume = 1; initAudioBoost(); gainNode.gain.value = val; volumeBar.classList.add('boosted'); }
            volumeBar.value = val;
            volPercent.innerText = Math.round(val * 100) + '%';
            updateVolIcon(val);
        }
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

        // --- CONTROLS ---
        video.addEventListener('loadedmetadata', () => { 
            seekBar.max = video.duration; 
            document.getElementById('totalTime').innerText = formatTime(video.duration);
        });
        video.addEventListener('timeupdate', () => { 
            if (!seekBar.dragging) seekBar.value = video.currentTime; 
            document.getElementById('currentTime').innerText = formatTime(video.currentTime);
        });
        
        seekBar.onmousedown = () => seekBar.dragging = true;
        seekBar.onmouseup = () => { video.currentTime = seekBar.value; seekBar.dragging = false; };
        seekBar.oninput = (e) => { document.getElementById('currentTime').innerText = formatTime(e.target.value); };

        function togglePlay() { 
            if (video.paused) { video.play(); playIcon.className = "fas fa-pause"; showControls(); } 
            else { video.pause(); playIcon.className = "fas fa-play"; clearTimeout(hideTimer); body.classList.remove('ui-hidden'); } 
        }
        function seekRelative(s) { video.currentTime += s; showControls(); }
        function toggleFullScreen() { if (!document.fullscreenElement) document.documentElement.requestFullscreen(); else document.exitFullscreen(); }
        function formatTime(s) { 
            if(isNaN(s)) return "00:00";
            let h = Math.floor(s / 3600); let m = Math.floor((s % 3600) / 60); let sc = Math.floor(s % 60); 
            if (h > 0) return `${h}:${m.toString().padStart(2,'0')}:${sc.toString().padStart(2,'0')}`; 
            return `${m}:${sc.toString().padStart(2,'0')}`; 
        }
        
        function showControls() { body.classList.remove('ui-hidden'); clearTimeout(hideTimer); hideTimer = setTimeout(() => { if (!video.paused) body.classList.add('ui-hidden'); }, 3000); }
        document.addEventListener('mousemove', showControls);
        video.addEventListener('waiting', () => spinner.style.display = 'block');
        video.addEventListener('playing', () => spinner.style.display = 'none');
    </script>
</body>
</html>
"""

# ==========================================
# BACKEND LOGIC
# ==========================================

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

def format_seconds(seconds):
    m, s = divmod(seconds, 60); h, m = divmod(m, 60)
    if h > 0: return f"{int(h)}:{int(m):02d}:{int(s):02d}"
    return f"{int(m)}:{int(s):02d}"

def get_video_codec_flags(quality, is_h264_source):
    if quality == 'original' and is_h264_source: return ['-c:v', 'copy']
    mode = CURRENT_HW_MODE 
    base = []
    if mode == 'nvenc': 
        base = ['-c:v', 'h264_nvenc', '-pix_fmt', 'yuv420p', '-preset', 'p2', '-profile:v', 'high', '-b:v', '5M', '-bufsize', '10M']
    elif mode == 'qsv': 
        base = ['-c:v', 'h264_qsv', '-preset', 'veryfast', '-pix_fmt', 'yuv420p']
    elif mode == 'videotoolbox': 
        base = ['-c:v', 'h264_videotoolbox', '-realtime', 'true', '-pix_fmt', 'yuv420p']
    elif mode == 'amf': 
        base = ['-c:v', 'h264_amf', '-usage', 'lowlatency', '-pix_fmt', 'yuv420p']
    else: 
        base = ['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-threads', '0', '-pix_fmt', 'yuv420p']
    if quality == '1080p': base.extend(['-vf', 'scale=-2:1080'])
    elif quality == '720p': base.extend(['-vf', 'scale=-2:720'])
    return base

# ==========================================
# ROUTES
# ==========================================

@app.route('/')
def index():
    return render_template_string(LANDING_TEMPLATE)

@app.route('/progress')
def progress_check():
    """Endpoint for polling download status."""
    return jsonify(download_state)

@app.route('/process_url', methods=['POST'])
def process_url():
    global download_state
    url = request.form.get('url')
    if not url: return jsonify({'status': 'error', 'message': 'Missing URL'})
    
    # Reset State
    download_state = {'progress': 0, 'status': 'Downloading', 'msg': 'Connecting...', 'filename': ''}
    
    # Clean previous downloads
    if os.path.exists(DOWNLOAD_DIR): shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR)

    filename = url.split('/')[-1] or "downloaded_file"
    save_path = os.path.join(DOWNLOAD_DIR, filename)
    download_state['filename'] = filename

    try:
        # Download with Progress Tracking
        download_state['msg'] = 'Starting Download...'
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_length = int(r.headers.get('content-length', 0))
            dl = 0
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    dl += len(chunk)
                    f.write(chunk)
                    if total_length > 0:
                        percent = int((dl / total_length) * 100)
                        download_state['progress'] = percent
                        download_state['msg'] = f"Downloading: {percent}%"
        
        download_state['progress'] = 100
        
        # Unzip if needed
        if zipfile.is_zipfile(save_path):
            download_state['msg'] = 'Extracting Zip Archive...'
            with zipfile.ZipFile(save_path, 'r') as z:
                z.extractall(DOWNLOAD_DIR)
            os.remove(save_path) # remove zip after extraction

        download_state['status'] = 'Done'
        download_state['msg'] = 'Finished!'
        
        return jsonify({'status': 'ok'})

    except Exception as e:
        download_state['status'] = 'Error'
        download_state['msg'] = str(e)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/list_files')
def list_files():
    video_exts = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
    files = []
    for root, dirs, filenames in os.walk(DOWNLOAD_DIR):
        for f in filenames:
            if f.lower().endswith(video_exts):
                full_path = os.path.join(root, f)
                files.append({'name': f, 'path': os.path.abspath(full_path)})
    
    if not files: return "No video files found in download.", 404
    return render_template_string(SELECTION_TEMPLATE, files=files)

@app.route('/set_and_play')
def set_and_play():
    global current_file_path
    mode = request.args.get('mode')
    path = request.args.get('path')
    if os.path.exists(path):
        current_file_path = path
        if mode == 'simple': return redirect(url_for('simple_player'))
        return redirect(url_for('advanced_player'))
    return "File not found", 404

@app.route('/play/advanced')
def advanced_player():
    if not current_file_path: return redirect(url_for('index'))
    # Load Metadata like original main.py
    audio_tracks, sub_tracks, duration, _ = get_media_info(current_file_path)
    
    # Safely select an audio track if available, else 'None'
    current_audio = request.args.get('audio_index')
    if not current_audio and audio_tracks: 
        current_audio = list(audio_tracks.keys())[0]
    elif not current_audio and not audio_tracks:
        current_audio = 'None'
    
    return render_template_string(
        ADVANCED_TEMPLATE, filename=os.path.basename(current_file_path),
        audio_tracks=audio_tracks, sub_tracks=sub_tracks, current_audio=current_audio,
        current_quality="original", duration=duration, duration_formatted=format_seconds(duration),
        start_time=0, hw_modes=AVAILABLE_HW_MODES, current_hw=CURRENT_HW_MODE
    )

@app.route('/play/simple')
def simple_player():
    if not current_file_path: return redirect(url_for('index'))
    # Simple needs duration for UI
    _, _, duration, _ = get_media_info(current_file_path)
    return render_template_string(
        SIMPLE_TEMPLATE, 
        duration_formatted=format_seconds(duration)
    )

# --- ADVANCED PLAYER ROUTES (UNCHANGED LOGIC) ---
@app.route('/set_hw')
def set_hw():
    global CURRENT_HW_MODE
    new_mode = request.args.get('mode')
    if new_mode in AVAILABLE_HW_MODES:
        CURRENT_HW_MODE = new_mode
        logger.info(f"Switched Hardware Engine to: {AVAILABLE_HW_MODES[new_mode]}")
        return "OK"
    return "Invalid", 400

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

    # Get media info to check audio existence
    audio_tracks, _, _, is_h264 = get_media_info(current_file_path)
    
    input_flags = ['-ss', str(start_time)]
    cmd = ['ffmpeg'] + input_flags + ['-i', current_file_path, '-map', '0:v:0']

    # --- AUDIO CHECK ---
    # Only map audio if valid tracks exist and index is valid
    if audio_tracks and audio_index in audio_tracks:
        cmd.extend(['-map', f'0:{audio_index}'])
        # Transcode audio to Stereo AAC
        cmd.extend(['-c:a', 'aac', '-ac', '2', '-b:a', '192k'])
    else:
        # No audio track? Do not map audio.
        logger.info("No audio track detected or selected. Streaming video only.")
        # If no audio, just video flags
    
    cmd.extend(get_video_codec_flags(quality, is_h264))
    
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

# --- SIMPLE PLAYER ROUTE (Raw Range Requests) ---
@app.route('/raw_stream')
def raw_stream():
    """Serves the raw file using a generator to prevent RAM spikes."""
    if not current_file_path: return "No file", 404
    
    file_size = os.path.getsize(current_file_path)
    range_header = request.headers.get('Range', None)

    # If no range header, send the whole file (flask send_file handles streaming automatically)
    if not range_header:
        return send_file(current_file_path)

    # Parse Range Header
    byte1, byte2 = 0, None
    m = re.search(r'(\d+)-(\d*)', range_header)
    g = m.groups()

    if g[0]: byte1 = int(g[0])
    if g[1]: byte2 = int(g[1])

    # Calculate length
    if byte2 is not None:
        length = byte2 + 1 - byte1
    else:
        length = file_size - byte1

    # generator to stream file in 8KB chunks
    def generate():
        try:
            with open(current_file_path, 'rb') as f:
                f.seek(byte1)
                remaining = length
                chunk_size = 8192 
                while remaining > 0:
                    # Read whichever is smaller: the standard chunk or remaining bytes
                    read_size = min(chunk_size, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
        except Exception as e:
            logger.error(f"Stream Error: {e}")

    # Set byte2 for the header if it was None
    end_byte = byte2 if byte2 is not None else file_size - 1

    rv = Response(
        generate(), 
        206, 
        mimetype=mimetypes.guess_type(current_file_path)[0], 
        direct_passthrough=True
    )
    rv.headers.add('Content-Range', f'bytes {byte1}-{end_byte}/{file_size}')
    rv.headers.add('Accept-Ranges', 'bytes')
    return rv

if __name__ == '__main__':
    print("---------------------------------------")
    print(" 🚀 UNIFIED PLAYER LAUNCHED")
    print(f" Available Modes: {list(AVAILABLE_HW_MODES.keys())}")
    print(" Go to: http://127.0.0.1:5500")
    print("---------------------------------------")
    serve(app, host='0.0.0.0', port=5500, threads=10)