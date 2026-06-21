import os
import shutil
import json
import tkinter as tk
from tkinter import filedialog
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify, send_file
import webbrowser
import threading
import time

# ================= CONFIGURATION =================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(SCRIPT_DIR, "cache")

SETTINGS_FILE = os.path.join(CACHE_DIR, "settings.json")
PROGRESS_FILE = os.path.join(CACHE_DIR, "progress.json")
NOTES_FILE = os.path.join(CACHE_DIR, "notes.json")
FLAGS_FILE = os.path.join(CACHE_DIR, "flags.json")
STATS_FILE = os.path.join(CACHE_DIR, "user_stats.json")
DRAWINGS_FILE = os.path.join(CACHE_DIR, "drawings.json") # NEW: Tactical Canvas Cache

BASE_DIR = None

app = Flask(__name__)

# ================= HELPERS =================
def load_json(filepath):
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_json(filepath, data):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    with open(filepath, 'w') as f:
        json.dump(data, f)

def ask_for_directory(initial_dir=None):
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.withdraw()
    folder_path = filedialog.askdirectory(initialdir=initial_dir, title="Select your Study Materials Folder (Semester 3)")
    root.destroy()
    return folder_path

def init_base_dir():
    global BASE_DIR
    settings = load_json(SETTINGS_FILE)
    stored_dir = settings.get("base_dir")
    
    if not stored_dir or not os.path.exists(stored_dir):
        print("\n[!] No valid study directory found in cache.")
        print("[*] Opening folder selection dialog...")
        stored_dir = ask_for_directory()
        if not stored_dir:
            print("[X] No folder selected. Application terminating.")
            os._exit(1)
        settings["base_dir"] = stored_dir
        save_json(SETTINGS_FILE, settings)
        print(f"[+] Study directory linked: {stored_dir}\n")
    BASE_DIR = stored_dir

def get_stats():
    stats = load_json(STATS_FILE)
    if not stats:
        stats = {"xp": 0, "level": 1, "streak": 0, "last_login": "", "daily_xp": {}, "badges": []}
    return stats

def save_stats(stats): save_json(STATS_FILE, stats)

def update_streak():
    stats = get_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if stats["last_login"] != today:
        if stats["last_login"] == yesterday: stats["streak"] += 1
        else: stats["streak"] = 1
        stats["last_login"] = today
        save_stats(stats)
        check_badges(stats, "login")

def add_xp(amount):
    stats = get_stats()
    stats["xp"] = max(0, stats["xp"] + amount)
    stats["level"] = 1 + (stats["xp"] // 100)
    today = datetime.now().strftime("%Y-%m-%d")
    stats["daily_xp"][today] = stats["daily_xp"].get(today, 0) + amount
    save_stats(stats)
    if amount > 0: check_badges(stats, "xp")
    return stats

def check_badges(stats, context):
    badges = set(stats["badges"])
    now = datetime.now()
    if context == "login":
        if stats["streak"] >= 3: badges.add("Streak Master")
        if stats["streak"] >= 7: badges.add("On Fire")
        if now.weekday() >= 5: badges.add("Weekend Warrior")
    if context == "xp":
        if stats["xp"] >= 100: badges.add("Scholar")
        if stats["xp"] >= 1000: badges.add("Professor")
    if context == "action":
        if now.hour >= 23 or now.hour < 4: badges.add("Night Owl")
    if len(badges) > len(stats["badges"]):
        stats["badges"] = list(badges)
        save_stats(stats)
        return True
    return False

# ================= HTML/JS/CSS FRONTEND =================
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skill Enhancer | Tactical Study Platform</title>
    <script src="{{ url_for('static', filename='css/tailwind.js') }}"></script>
    <link href="{{ url_for('static', filename='css/all.min.css') }}" rel="stylesheet">
    <style>
        :root { --bg-main: #0f172a; --bg-sec: #1e293b; --text-main: #e2e8f0; --border: #334155; --grid-cols: 6; }
        body { background-color: var(--bg-main); color: var(--text-main); transition: background-color 0.3s; }
        body.light-mode { --bg-main: #f8fafc; --bg-sec: #ffffff; --text-main: #1e293b; --border: #cbd5e1; }
        body.light-mode .bg-slate-900 { background-color: #ffffff !important; border-color: #e2e8f0 !important; color: #0f172a !important; }
        body.light-mode .bg-slate-800 { background-color: #f1f5f9 !important; border-color: #cbd5e1 !important; }
        body.light-mode .bg-slate-700\\/50 { background-color: #ffffff !important; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        body.light-mode .text-slate-300 { color: #475569 !important; }
        body.light-mode .text-slate-400 { color: #64748b !important; }
        body.light-mode .text-white { color: #1e293b !important; }
        body.light-mode .hover\\:text-white:hover { color: #0f172a !important; }
        body.light-mode .modal-content { background-color: #ffffff !important; color: #1e293b !important; }
        body.light-mode input, body.light-mode select, body.light-mode textarea { background-color: #ffffff !important; border-color: #cbd5e1 !important; color: #1e293b !important; }

        .tree-node { padding: 4px 8px; cursor: pointer; border-radius: 4px; display: flex; align-items: center; gap: 8px; font-size: 0.9rem; }
        .tree-node:hover { background-color: var(--bg-sec); color: #3b82f6; }
        .tree-node.active { background-color: #3b82f6 !important; color: white !important; }
        .tree-children { margin-left: 16px; border-left: 1px solid var(--border); }
        .tree-node.drag-over { background-color: #3b82f6 !important; color: white !important; outline: 2px dashed white; }

        #main-grid { display: grid; grid-template-columns: repeat(var(--grid-cols), minmax(0, 1fr)); gap: 1rem; }
        .grid-item { transition: all 0.2s; border: 1px solid transparent; }
        .grid-item:hover { background-color: var(--bg-sec); transform: translateY(-2px); border-color: #3b82f6; }
        .icon-box { height: 60px; display: flex; align-items: center; justify-content: center; }
        
        .glow-done { box-shadow: 0 0 15px rgba(74, 222, 128, 0.3), inset 0 0 10px rgba(74, 222, 128, 0.1); border-color: rgba(74, 222, 128, 0.5) !important; background-color: rgba(74, 222, 128, 0.05) !important; }
        .glow-done .icon-box i { color: #4ade80 !important; }
        .glow-flag { box-shadow: 0 0 15px rgba(250, 204, 21, 0.3), inset 0 0 10px rgba(250, 204, 21, 0.1); border-color: rgba(250, 204, 21, 0.5) !important; background-color: rgba(250, 204, 21, 0.05) !important; }
        .glow-flag .icon-box i { color: #facc15 !important; }
        
        .badge { font-size: 0.7rem; padding: 2px 6px; border-radius: 999px; font-weight: bold; text-transform: uppercase; border: 1px solid currentColor; }
        .badge-gold { color: #facc15; background: rgba(250, 204, 21, 0.1); }
        .badge-blue { color: #60a5fa; background: rgba(96, 165, 250, 0.1); }
        .badge-red { color: #f87171; background: rgba(248, 113, 113, 0.1); }
        .badge-purple { color: #c084fc; background: rgba(192, 132, 252, 0.1); }

        input[type=range] { -webkit-appearance: none; background: transparent; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; height: 16px; width: 16px; border-radius: 50%; background: #3b82f6; margin-top: -6px; cursor: pointer; }
        input[type=range]::-webkit-slider-runnable-track { width: 100%; height: 4px; cursor: pointer; background: #334155; border-radius: 2px; }
        
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #475569; border-radius: 4px; }
        .animate-fade-in { animation: fadeIn 0.2s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
        
        /* Tool Button Focus */
        .tool-btn.active { outline: 2px solid white; transform: scale(1.1); }
    </style>
</head>
<body class="h-screen flex flex-col overflow-hidden">

    <header class="bg-slate-900 border-b border-slate-700 h-16 flex items-center px-4 justify-between shrink-0">
        <div class="flex items-center gap-4 flex-1">
            <div class="flex items-center gap-2 shrink-0">
                <i class="fa-solid fa-graduation-cap text-2xl text-blue-500"></i>
                <h1 class="font-bold text-lg tracking-wide text-white hidden md:block">Skill Enhancer</h1>
            </div>
            
            <div class="flex-1 max-w-3xl mx-6 flex flex-col justify-center">
                 <div class="flex justify-between text-[10px] text-slate-400 mb-1 uppercase tracking-wider font-bold">
                    <span>Checkpoint <span id="currentCheckpoint">1</span></span>
                    <span id="streakBadge" class="text-orange-500 hidden"><i class="fa-solid fa-fire"></i> <span id="streakVal">0</span> Day Streak</span>
                    <span>Checkpoint <span id="nextCheckpoint">2</span></span>
                 </div>
                 <div class="w-full h-3 bg-slate-800 rounded-full border border-slate-700 relative overflow-hidden shadow-inner">
                    <div class="absolute inset-0 flex justify-between px-2">
                         <div class="w-px h-full bg-slate-700/50"></div><div class="w-px h-full bg-slate-700/50"></div><div class="w-px h-full bg-slate-700/50"></div><div class="w-px h-full bg-slate-700/50"></div><div class="w-px h-full bg-slate-700/50"></div>
                    </div>
                    <div id="timelineBar" class="h-full bg-gradient-to-r from-blue-600 via-purple-500 to-pink-500 transition-all duration-700 ease-out shadow-[0_0_10px_rgba(59,130,246,0.5)]" style="width: 0%"></div>
                 </div>
            </div>
        </div>

        <div class="flex items-center gap-3">
             <button onclick="toggleTheme()" class="text-slate-400 hover:text-white transition" title="Toggle Theme"><i class="fa-solid fa-sun" id="themeIcon"></i></button>
             <button onclick="changeStudyFolder()" class="text-slate-400 hover:text-blue-400 transition" title="Change Source Directory"><i class="fa-solid fa-folder-tree"></i></button>
             <div class="h-6 w-px bg-slate-700 mx-1"></div>
             <button onclick="fetchTree()" class="text-slate-400 hover:text-white transition" title="Refresh"><i class="fa-solid fa-sync"></i></button>
        </div>
    </header>

    <div class="flex-1 flex overflow-hidden">
        <aside class="w-64 bg-slate-900 border-r border-slate-700 flex flex-col transition-colors duration-300">
            <div class="p-3 text-xs font-bold text-slate-500 uppercase tracking-wider flex justify-between">Folders</div>
            <div id="sidebar-tree" class="flex-1 overflow-y-auto p-2 space-y-1"></div>
            <div class="p-3 border-t border-slate-700 bg-slate-800/50">
                <div class="text-[10px] font-bold text-slate-500 uppercase mb-2">My Badges</div>
                <div id="badgeContainer" class="flex flex-wrap gap-2"><span class="text-xs text-slate-500 italic">No badges yet...</span></div>
            </div>
        </aside>

        <main class="flex-1 flex flex-col bg-slate-800 relative transition-colors duration-300">
            <div class="h-14 border-b border-slate-700 flex items-center px-4 gap-3 bg-slate-800/95 backdrop-blur z-10 transition-colors duration-300">
                <button onclick="goUp()" class="p-2 hover:bg-slate-700 rounded-full hover:text-blue-400 disabled:opacity-30 transition" id="btn-up"><i class="fa-solid fa-arrow-up"></i></button>
                <div class="flex-1 flex flex-col justify-center overflow-hidden">
                    <div id="breadcrumb" class="text-xs text-slate-400 truncate font-mono mb-1"></div>
                    <div class="w-full max-w-md h-2 bg-slate-700 rounded-full overflow-hidden flex"><div id="progressBar" class="h-full bg-green-500 transition-all duration-500" style="width: 0%"></div></div>
                    <div id="progressText" class="text-[10px] text-slate-400 absolute top-9 left-16 ml-1">0/0</div>
                </div>
                <div class="flex items-center gap-2 mx-4 group">
                    <i class="fa-solid fa-border-all text-slate-500 text-xs"></i>
                    <input type="range" min="2" max="10" value="6" class="w-20 accent-blue-500" oninput="updateGridColumns(this.value)" title="Grid Size">
                </div>
                <button onclick="shufflePlay()" class="p-2 text-slate-300 hover:text-purple-400 hover:bg-slate-700 rounded-lg transition" title="Shuffle Question"><i class="fa-solid fa-dice text-lg"></i></button>
                <div class="h-6 w-px bg-slate-700 mx-1"></div>
                <button onclick="promptCreate()" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-xs text-white font-medium shadow-lg"><i class="fa-solid fa-plus mr-1"></i> Folder</button>
            </div>
            <div id="main-grid" class="flex-1 overflow-y-auto p-6"></div>
            <div id="loader" class="absolute inset-0 bg-slate-900/50 flex items-center justify-center z-20 hidden"><i class="fa-solid fa-circle-notch fa-spin text-4xl text-blue-500"></i></div>
        </main>
    </div>

    <div id="previewModal" class="fixed inset-0 bg-black/95 hidden flex flex-col z-50 animate-fade-in">
        <div class="h-14 flex justify-between items-center px-6 text-white bg-slate-900 border-b border-slate-700 shrink-0">
            <span id="previewTitle" class="font-medium truncate text-lg w-2/3 text-white">Preview</span>
            <div class="flex items-center gap-4">
                <span class="text-xs text-slate-400 hidden md:inline"><kbd class="bg-slate-700 px-1 rounded">Space</kbd> Done &nbsp; <kbd class="bg-slate-700 px-1 rounded">→</kbd> Next &nbsp; <kbd class="bg-slate-700 px-1 rounded">F</kbd> Flag</span>
                <button onclick="closePreview()" class="text-slate-400 hover:text-white text-2xl transition"><i class="fa-solid fa-xmark"></i></button>
            </div>
        </div>
        <div class="flex-1 flex overflow-hidden">
            
            <div class="flex-1 flex items-center justify-center p-4 bg-black/50 relative backdrop-blur-sm overflow-hidden" id="canvasContainer">
                
                <div class="relative shadow-2xl inline-block" id="imageWrapper">
                    <img id="previewImage" src="" class="max-w-full max-h-[80vh] rounded block" ondragstart="return false;">
                    <canvas id="vectorCanvas" class="absolute top-0 left-0 w-full h-full cursor-crosshair rounded hidden"></canvas>
                    
                    <div id="canvasToolbar" class="absolute top-4 left-4 bg-slate-900/90 p-2 rounded-lg border border-slate-700 flex flex-col gap-3 shadow-lg hidden z-10 transition-colors">
                        <button onclick="setDrawColor('#ef4444', this)" class="tool-btn active w-5 h-5 rounded-full bg-red-500 transition shadow-[0_0_8px_#ef4444]" title="Red Force Vector"></button>
                        <button onclick="setDrawColor('#3b82f6', this)" class="tool-btn w-5 h-5 rounded-full bg-blue-500 transition shadow-[0_0_8px_#3b82f6]" title="Blue Acceleration"></button>
                        <button onclick="setDrawColor('#22c55e', this)" class="tool-btn w-5 h-5 rounded-full bg-green-500 transition shadow-[0_0_8px_#22c55e]" title="Green Kinematics"></button>
                        <button onclick="setDrawColor('#eab308', this)" class="tool-btn w-5 h-5 rounded-full bg-yellow-500 transition shadow-[0_0_8px_#eab308]" title="Yellow Highlight"></button>
                        <div class="w-full h-px bg-slate-600 my-1"></div>
                        <button onclick="clearCanvas()" class="text-slate-400 hover:text-red-400 p-1 transition" title="Clear All Vectors"><i class="fa-solid fa-trash-can text-sm"></i></button>
                    </div>
                </div>

                <div id="previewUnsupported" class="hidden text-slate-400 text-center absolute inset-0 flex flex-col items-center justify-center">
                    <i class="fa-regular fa-file text-6xl mb-4"></i>
                    <p>No preview available.</p>
                </div>
            </div>

            <div class="w-80 bg-slate-900 border-l border-slate-700 p-4 flex flex-col shrink-0 transition-colors duration-300">
                <h3 class="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">My Notes</h3>
                <textarea id="noteInput" class="flex-1 bg-slate-800 border border-slate-700 rounded p-3 text-slate-200 text-sm focus:outline-none focus:border-blue-500 resize-none placeholder-slate-600" placeholder="Write formulas, hints, or key points here..."></textarea>
                <div class="text-xs text-slate-500 mt-2 text-right" id="noteStatus">Auto-saved</div>
            </div>
        </div>
        <div class="h-20 bg-slate-900 border-t border-slate-700 flex items-center justify-center gap-6 shrink-0 transition-colors duration-300">
            <button onclick="toggleFlag()" id="btnFlag" class="flex items-center gap-2 px-6 py-3 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 transition"><i class="fa-solid fa-flag"></i> Flag (F)</button>
            <button onclick="toggleDone()" id="btnDone" class="flex items-center gap-2 px-8 py-3 rounded-lg bg-green-600 hover:bg-green-500 text-white font-bold shadow-lg shadow-green-900/50 transition transform hover:scale-105"><i class="fa-solid fa-check"></i> Done (Space)</button>
        </div>
    </div>

    <div id="actionModal" class="fixed inset-0 bg-black/70 hidden flex items-center justify-center z-50">
        <div class="bg-slate-800 rounded-xl shadow-2xl p-6 w-96 border border-slate-600 transform scale-100 transition-all modal-content">
            <h2 id="modalTitle" class="text-xl font-bold mb-4 text-white">Action</h2>
            <input type="text" id="modalInput" class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-white mb-4 focus:outline-none focus:border-blue-500">
            <div id="moveUI" class="hidden mb-4"><p class="text-sm text-slate-400 mb-2">Move to:</p><select id="moveSelect" class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-white text-sm"></select></div>
            <div class="flex justify-end gap-2">
                <button onclick="closeModal()" class="px-4 py-2 rounded text-slate-300 hover:text-white hover:bg-slate-700">Cancel</button>
                <button id="modalConfirmBtn" class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-500 font-medium">Confirm</button>
            </div>
        </div>
    </div>

    <script>
        let rootData = null; let currentFolder = null; let currentPreviewItem = null;
        let allFoldersList = []; let rootPathStr = ""; let noteTimeout = null;

        // CANVAS VARIABLES
        const canvas = document.getElementById('vectorCanvas');
        const ctx = canvas.getContext('2d');
        let isDrawing = false;
        let currentColor = '#ef4444';

        fetchTree(); fetchStats();

        async function fetchTree() {
            document.getElementById('loader').classList.remove('hidden');
            try {
                const res = await fetch('/api/tree');
                const data = await res.json();
                if(data.error) { alert("Error loading directory. Please select a valid folder."); return; }
                rootData = data.structure; rootPathStr = data.root;
                
                if (!currentFolder || !findNode(rootData, currentFolder.path)) currentFolder = rootData;
                else currentFolder = findNode(rootData, currentFolder.path);

                const sidebar = document.getElementById('sidebar-tree'); sidebar.innerHTML = ''; 
                renderSidebar(rootData, sidebar); updateMainView();
            } catch (e) { console.error(e); } 
            finally { document.getElementById('loader').classList.add('hidden'); }
        }

        async function fetchStats() {
            try {
                const res = await fetch('/api/stats'); const stats = await res.json();
                document.getElementById('currentCheckpoint').innerText = stats.level;
                document.getElementById('nextCheckpoint').innerText = stats.level + 1;
                document.getElementById('timelineBar').style.width = `${stats.xp % 100}%`;
                
                if(stats.streak > 0) { document.getElementById('streakBadge').classList.remove('hidden'); document.getElementById('streakVal').innerText = stats.streak; } 
                else document.getElementById('streakBadge').classList.add('hidden');

                const badgeContainer = document.getElementById('badgeContainer');
                if(stats.badges.length > 0) {
                    badgeContainer.innerHTML = '';
                    stats.badges.forEach(b => {
                        let color = 'badge-blue';
                        if(b.includes('Fire') || b.includes('Master')) color = 'badge-red';
                        if(b.includes('Scholar') || b.includes('Professor')) color = 'badge-purple';
                        if(b.includes('Warrior') || b.includes('Owl')) color = 'badge-gold';
                        const span = document.createElement('span'); span.className = `badge ${color}`; span.innerText = b; badgeContainer.appendChild(span);
                    });
                }
            } catch(e) { console.error("Stats error", e); }
        }

        async function changeStudyFolder() {
            if(!confirm("Open selection dialog on your host computer to choose a new source folder?")) return;
            try {
                const res = await fetch('/api/change_dir', {method: 'POST'});
                const data = await res.json();
                if(data.success) { currentFolder = null; fetchTree(); } 
                else if(data.error) alert(data.error);
            } catch(e) { console.error(e); }
        }

        function updateGridColumns(val) { document.documentElement.style.setProperty('--grid-cols', val); }

        document.addEventListener('keydown', (e) => {
            if (document.getElementById('previewModal').classList.contains('hidden')) return;
            if (document.activeElement === document.getElementById('noteInput')) return;
            if (e.code === 'Space') { e.preventDefault(); toggleDone(); }
            if (e.key === 'ArrowRight') { e.preventDefault(); navigateImage(1); }
            if (e.key === 'ArrowLeft') { e.preventDefault(); navigateImage(-1); }
            if (e.key.toLowerCase() === 'f') { e.preventDefault(); toggleFlag(); }
            if (e.key === 'Escape') closePreview();
        });

        function navigateImage(direction) {
            if(!currentFolder.children) return;
            const items = currentFolder.children.filter(c => c.type === 'file' && isImage(c.name)).sort((a,b) => a.name.localeCompare(b.name));
            if(items.length === 0) return;
            const currentIndex = items.findIndex(i => i.path === currentPreviewItem.path);
            if(currentIndex === -1) return;
            let newIndex = currentIndex + direction;
            if(newIndex >= items.length) newIndex = 0;
            if(newIndex < 0) newIndex = items.length - 1;
            openPreview(items[newIndex]);
        }

        function drag(ev, path) { ev.dataTransfer.setData("text/plain", path); }
        function allowDrop(ev) { ev.preventDefault(); const target = ev.target.closest('.tree-node'); if(target) target.classList.add('drag-over'); }
        function dragLeave(ev) { const target = ev.target.closest('.tree-node'); if(target) target.classList.remove('drag-over'); }
        function drop(ev, destPath) {
            ev.preventDefault(); const target = ev.target.closest('.tree-node'); if(target) target.classList.remove('drag-over');
            const srcPath = ev.dataTransfer.getData("text/plain");
            if (srcPath && srcPath !== destPath) { if(confirm('Move file here?')) sendAction('/api/move', { src_path: srcPath, dest_folder: destPath }); }
        }

        function getFolderStats(node) {
            let total = 0; let done = 0;
            if (node.type === 'file') return { total: 1, done: node.done ? 1 : 0 };
            if (node.children) node.children.forEach(c => { const s = getFolderStats(c); total+=s.total; done+=s.done; });
            return { total, done };
        }
        function updateProgressUI() {
            const stats = getFolderStats(currentFolder);
            const pct = stats.total === 0 ? 0 : (stats.done / stats.total) * 100;
            document.getElementById('progressBar').style.width = `${pct}%`;
            document.getElementById('progressText').innerText = `${stats.done} / ${stats.total}`;
        }

        function renderSidebar(node, container) {
            if (node.type !== 'directory') return;
            const div = document.createElement('div');
            const isRoot = node.path === rootPathStr;
            const activeClass = (currentFolder && currentFolder.path === node.path) ? 'active' : '';
            
            const titleRow = document.createElement('div');
            titleRow.className = `tree-node ${activeClass}`;
            titleRow.onclick = (e) => { e.stopPropagation(); selectFolder(node); };
            titleRow.ondragover = (e) => allowDrop(e); titleRow.ondragleave = (e) => dragLeave(e); titleRow.ondrop = (e) => drop(e, node.path);
            titleRow.innerHTML = `<i class="fa-regular fa-folder-open"></i> <span class="truncate">${isRoot ? 'Workspace Base' : node.name}</span>`;
            div.appendChild(titleRow);

            if (node.children && node.children.length > 0) {
                const childrenContainer = document.createElement('div'); childrenContainer.className = 'tree-children';
                const folders = node.children.filter(c => c.type === 'directory');
                folders.forEach(child => renderSidebar(child, childrenContainer));
                if (folders.length > 0) div.appendChild(childrenContainer);
            }
            container.appendChild(div);
        }

        function updateMainView() {
            const grid = document.getElementById('main-grid'); grid.innerHTML = '';
            let displayPath = currentFolder.path.replace(rootPathStr, 'Workspace Base').replace(/\\\\/g, '/');
            document.getElementById('breadcrumb').innerText = displayPath; updateProgressUI();
            
            const items = (currentFolder.children || []).sort((a,b) => {
                if (a.type === b.type) return a.name.localeCompare(b.name);
                return a.type === 'directory' ? -1 : 1;
            });

            if (items.length === 0) { grid.innerHTML = `<div class="col-span-full text-center text-slate-500 mt-10">Empty Folder</div>`; return; }

            items.forEach(item => {
                const isDir = item.type === 'directory';
                let classes = 'grid-item bg-slate-700/50 rounded-lg p-3 cursor-pointer group relative ';
                if (item.done) classes += 'glow-done '; else if (item.flagged) classes += 'glow-flag ';
                
                const el = document.createElement('div'); el.className = classes; el.title = item.name;
                if(!isDir) { el.draggable = true; el.ondragstart = (e) => drag(e, item.path); }

                let iconHtml = isDir ? `<i class="fa-solid fa-folder text-4xl text-yellow-500"></i>` :
                               isImage(item.name) ? `<i class="fa-solid fa-image text-4xl text-purple-400"></i>` : `<i class="fa-solid fa-file-lines text-4xl text-slate-400"></i>`;

                let badges = '';
                if(item.done) badges += `<div class="absolute top-2 left-2 text-green-400 text-xs"><i class="fa-solid fa-check-circle"></i></div>`;
                if(item.flagged) badges += `<div class="absolute top-2 right-2 text-yellow-400 text-xs"><i class="fa-solid fa-flag"></i></div>`;
                if(item.note) badges += `<div class="absolute bottom-2 right-2 text-slate-400 text-[10px]"><i class="fa-solid fa-comment-dots"></i></div>`;

                const safePath = item.path.replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'");
                const safeName = item.name.replace(/'/g, "\\\\'");

                el.innerHTML = `${badges}<div class="icon-box mb-2">${iconHtml}</div><div class="text-center text-xs text-slate-300 truncate font-medium px-1">${item.name}</div>
                    <div class="absolute top-1 right-1 hidden group-hover:flex gap-1 bg-slate-800 rounded p-1 shadow-lg z-10">
                        <button onclick="event.stopPropagation(); promptRename('${safePath}', '${safeName}')" class="text-blue-400 hover:text-white p-1"><i class="fa-solid fa-pen"></i></button>
                        <button onclick="event.stopPropagation(); deleteItem('${safePath}')" class="text-red-400 hover:text-white p-1"><i class="fa-solid fa-trash"></i></button>
                        ${!isDir ? `<button onclick="event.stopPropagation(); promptMove('${safePath}')" class="text-green-400 hover:text-white p-1"><i class="fa-solid fa-share"></i></button>` : ''}
                    </div>`;
                el.onclick = () => { if (isDir) selectFolder(item); else if (isImage(item.name)) openPreview(item); };
                grid.appendChild(el);
            });
            document.getElementById('btn-up').disabled = (currentFolder.path === rootPathStr);
        }

        function shufflePlay() {
            if(!currentFolder.children) return;
            const files = currentFolder.children.filter(c => c.type === 'file' && isImage(c.name));
            if(files.length === 0) { alert("No images here!"); return; }
            openPreview(files[Math.floor(Math.random() * files.length)]);
        }

        // ================= VECTOR CANVAS LOGIC =================

        function setDrawColor(color, btn) {
            currentColor = color;
            document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
            if(btn) btn.classList.add('active');
        }

        function getMousePos(evt) {
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            return {
                x: (evt.clientX - rect.left) * scaleX,
                y: (evt.clientY - rect.top) * scaleY
            };
        }

        canvas.addEventListener('mousedown', (e) => {
            isDrawing = true;
            const pos = getMousePos(e);
            ctx.beginPath();
            ctx.moveTo(pos.x, pos.y);
            ctx.strokeStyle = currentColor;
            ctx.lineWidth = 4;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
        });

        canvas.addEventListener('mousemove', (e) => {
            if (!isDrawing) return;
            const pos = getMousePos(e);
            ctx.lineTo(pos.x, pos.y);
            ctx.stroke();
        });

        canvas.addEventListener('mouseup', () => { if(isDrawing) { isDrawing = false; saveCanvasState(); }});
        canvas.addEventListener('mouseout', () => { if(isDrawing) { isDrawing = false; saveCanvasState(); }});

        function clearCanvas() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            saveCanvasState();
        }

        async function saveCanvasState() {
            if(!currentPreviewItem) return;
            const dataURL = canvas.toDataURL('image/png');
            try {
                await fetch('/api/drawing', { 
                    method: 'POST', 
                    headers: {'Content-Type': 'application/json'}, 
                    body: JSON.stringify({ path: currentPreviewItem.path, drawing: dataURL }) 
                });
            } catch(e) { console.error("Error saving drawing:", e); }
        }

        // Must calculate dimension after image fully loads so overlay perfectly matches
        document.getElementById('previewImage').onload = async function() {
            canvas.width = this.width;
            canvas.height = this.height;
            canvas.classList.remove('hidden');
            document.getElementById('canvasToolbar').classList.remove('hidden');
            
            // Load saved drawing from backend
            try {
                const res = await fetch(`/api/drawing?path=${encodeURIComponent(currentPreviewItem.path)}`);
                const data = await res.json();
                if (data.drawing) {
                    const drawingImg = new Image();
                    drawingImg.onload = () => ctx.drawImage(drawingImg, 0, 0, canvas.width, canvas.height);
                    drawingImg.src = data.drawing;
                }
            } catch(e) { console.error("Could not load drawing data"); }
        };

        // ========================================================

        function openPreview(item) {
            currentPreviewItem = item; 
            document.getElementById('previewTitle').innerText = item.name; 
            document.getElementById('previewModal').classList.remove('hidden');
            
            const img = document.getElementById('previewImage'); 
            const unsupp = document.getElementById('previewUnsupported');
            
            // Reset Canvas state before loading new image
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            canvas.classList.add('hidden');
            document.getElementById('canvasToolbar').classList.add('hidden');

            if (isImage(item.name)) { 
                img.src = `/api/file?path=${encodeURIComponent(item.path)}`; 
                img.classList.remove('hidden'); 
                unsupp.classList.add('hidden'); 
            } else { 
                img.classList.add('hidden'); 
                unsupp.classList.remove('hidden'); 
            }
            
            updatePreviewButtons();
            
            const noteInput = document.getElementById('noteInput'); 
            noteInput.value = item.note || "";
            noteInput.oninput = () => { 
                document.getElementById('noteStatus').innerText = "Typing..."; 
                clearTimeout(noteTimeout); 
                noteTimeout = setTimeout(saveNote, 1000); 
            };
        }

        function updatePreviewButtons() {
            const btnFlag = document.getElementById('btnFlag'); const btnDone = document.getElementById('btnDone');
            if(currentPreviewItem.flagged) btnFlag.className = "flex items-center gap-2 px-6 py-3 rounded-lg bg-yellow-600 text-white font-bold transition";
            else btnFlag.className = "flex items-center gap-2 px-6 py-3 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 transition";
            if(currentPreviewItem.done) { btnDone.innerHTML = `<i class="fa-solid fa-rotate-left"></i> Undone`; btnDone.className = "flex items-center gap-2 px-8 py-3 rounded-lg bg-slate-600 hover:bg-slate-500 text-white font-medium transition"; } 
            else { btnDone.innerHTML = `<i class="fa-solid fa-check"></i> Done`; btnDone.className = "flex items-center gap-2 px-8 py-3 rounded-lg bg-green-600 hover:bg-green-500 text-white font-bold shadow-lg shadow-green-900/50 transition transform hover:scale-105"; }
        }
        
        function closePreview() { 
            document.getElementById('previewModal').classList.add('hidden'); 
            document.getElementById('previewImage').src = ""; 
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            currentPreviewItem = null; 
        }

        async function saveNote() {
            if(!currentPreviewItem) return; const text = document.getElementById('noteInput').value;
            try { await fetch('/api/note', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ path: currentPreviewItem.path, note: text }) }); document.getElementById('noteStatus').innerText = "Saved"; currentPreviewItem.note = text; updateMainView(); } catch(e) { console.error(e); }
        }
        async function toggleDone() {
            if(!currentPreviewItem) return; const newState = !currentPreviewItem.done; currentPreviewItem.done = newState; updatePreviewButtons();
            await sendStatusUpdate('done', newState); if(newState) closePreview(); 
        }
        async function toggleFlag() { if(!currentPreviewItem) return; const newState = !currentPreviewItem.flagged; currentPreviewItem.flagged = newState; updatePreviewButtons(); await sendStatusUpdate('flag', newState); }
        async function sendStatusUpdate(type, value) { try { const res = await fetch('/api/status', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ path: currentPreviewItem.path, type: type, value: value }) }); if((await res.json()).success) { await fetchTree(); await fetchStats(); } } catch(e) { alert("Error saving"); } }

        function selectFolder(node) { currentFolder = node; const sidebar = document.getElementById('sidebar-tree'); sidebar.innerHTML = ''; renderSidebar(rootData, sidebar); updateMainView(); }
        function findNode(node, path) { if (node.path === path) return node; if (node.children) { for (let child of node.children) { const found = findNode(child, path); if (found) return found; } } return null; }
        function goUp() { if (currentFolder.path === rootPathStr) return; const parentPath = currentFolder.path.substring(0, currentFolder.path.lastIndexOf(isWindowsPath(currentFolder.path) ? '\\\\' : '/')); const parentNode = findNode(rootData, parentPath); if (parentNode) selectFolder(parentNode); }
        function isWindowsPath(path) { return path.includes('\\\\'); }
        function isImage(filename) { return /\\.(jpg|jpeg|png|gif|webp|bmp)$/i.test(filename); }
        function toggleTheme() { document.body.classList.toggle('light-mode'); const icon = document.getElementById('themeIcon'); if(document.body.classList.contains('light-mode')) { icon.classList.remove('fa-sun'); icon.classList.add('fa-moon'); } else { icon.classList.remove('fa-moon'); icon.classList.add('fa-sun'); } }

        function collectAllFolders(node) { if(node.type === 'directory') { allFoldersList.push(node); if(node.children) node.children.forEach(c => collectAllFolders(c)); } }
        async function sendAction(endpoint, payload) { const res = await fetch(endpoint, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) }); const data = await res.json(); if (data.success) { fetchTree(); closeModal(); } else alert("Error: " + data.error); }
        function promptCreate() { openModal('New Folder', '', (name) => { if(name) sendAction('/api/create', { path: currentFolder.path, name: name }); }); }
        function promptRename(path, oldName) { openModal('Rename', oldName, (newName) => { if (newName && newName !== oldName) sendAction('/api/rename', { path: path, new_name: newName }); }); }
        function deleteItem(path) { if(confirm('Delete?')) sendAction('/api/delete', { path: path }); }
        function promptMove(srcPath) {
            allFoldersList = []; collectAllFolders(rootData); const select = document.getElementById('moveSelect'); select.innerHTML = '';
            allFoldersList.forEach(f => { const opt = document.createElement('option'); opt.value = f.path; let relName = f.path.replace(rootPathStr, '').replace(/\\\\/g, '/'); opt.text = relName || "Root"; select.appendChild(opt); });
            openModal('Move File', '', (dest) => { sendAction('/api/move', { src_path: srcPath, dest_folder: document.getElementById('moveSelect').value }); }, true);
        }
        function openModal(title, val, onConfirm, isMove = false) {
            document.getElementById('modalTitle').innerText = title; const input = document.getElementById('modalInput'); const moveUI = document.getElementById('moveUI');
            input.value = val; if (isMove) { input.style.display = 'none'; moveUI.classList.remove('hidden'); } else { input.style.display = 'block'; moveUI.classList.add('hidden'); setTimeout(() => input.focus(), 50); }
            document.getElementById('actionModal').classList.remove('hidden'); const btn = document.getElementById('modalConfirmBtn'); const newBtn = btn.cloneNode(true); btn.parentNode.replaceChild(newBtn, btn);
            newBtn.onclick = () => onConfirm(input.value);
        }
        function closeModal() { document.getElementById('actionModal').classList.add('hidden'); }
    </script>
</body>
</html>
"""

# ================= BACKEND LOGIC =================

@app.route('/')
def index():
    update_streak()
    return render_template_string(html_template)

@app.route('/api/change_dir', methods=['POST'])
def change_dir_endpoint():
    global BASE_DIR
    new_dir = ask_for_directory(initial_dir=BASE_DIR)
    
    if new_dir:
        BASE_DIR = new_dir
        settings = load_json(SETTINGS_FILE)
        settings["base_dir"] = BASE_DIR
        save_json(SETTINGS_FILE, settings)
        return jsonify({"success": True, "new_dir": BASE_DIR})
    
    return jsonify({"success": False, "error": "Operation cancelled."})

@app.route('/api/tree')
def get_tree():
    if not BASE_DIR or not os.path.exists(BASE_DIR):
        return jsonify({"root": "", "structure": {}, "error": "Directory not found"})
    
    progress_data = load_json(PROGRESS_FILE)
    notes_data = load_json(NOTES_FILE)
    flags_data = load_json(FLAGS_FILE)

    def scan_dir(path):
        node = {"name": os.path.basename(path), "path": path, "type": "directory", "children": []}
        try:
            with os.scandir(path) as it:
                entries = sorted(list(it), key=lambda e: (not e.is_dir(), e.name.lower()))
                for entry in entries:
                    if entry.name == "cache": continue
                    if entry.is_dir():
                        node["children"].append(scan_dir(entry.path))
                    else:
                        node["children"].append({
                            "name": entry.name, "path": entry.path, "type": "file",
                            "done": progress_data.get(entry.path, False),
                            "flagged": flags_data.get(entry.path, False),
                            "note": notes_data.get(entry.path, "")
                        })
        except PermissionError: pass
        return node

    tree = scan_dir(BASE_DIR)
    tree["name"] = os.path.basename(BASE_DIR)
    return jsonify({"root": BASE_DIR, "structure": tree})

@app.route('/api/stats')
def stats_endpoint(): return jsonify(get_stats())

@app.route('/api/status', methods=['POST'])
def update_status():
    data = request.json
    path = data.get('path')
    type_ = data.get('type')
    value = data.get('value')
    
    file_map = {'done': PROGRESS_FILE, 'flag': FLAGS_FILE}
    target_file = file_map.get(type_)
    
    if target_file:
        store = load_json(target_file)
        if value: 
            store[path] = True
            if type_ == 'done':
                add_xp(10)
                check_badges(get_stats(), "action")
        elif path in store: 
            del store[path]
            if type_ == 'done': add_xp(-10)
        save_json(target_file, store)
        
    return jsonify({"success": True})

@app.route('/api/note', methods=['POST'])
def update_note():
    data = request.json
    path = data.get('path')
    note = data.get('note')
    
    notes = load_json(NOTES_FILE)
    if note and note.strip(): notes[path] = note
    elif path in notes: del notes[path]
    save_json(NOTES_FILE, notes)
    
    return jsonify({"success": True})

# === NEW: TACTICAL CANVAS API ENDPOINT ===
@app.route('/api/drawing', methods=['GET', 'POST'])
def handle_drawing():
    if request.method == 'POST':
        data = request.json
        path = data.get('path')
        drawing_data = data.get('drawing') # This is the Base64 image string
        
        drawings = load_json(DRAWINGS_FILE)
        if drawing_data:
            drawings[path] = drawing_data
        elif path in drawings:
            del drawings[path]
            
        save_json(DRAWINGS_FILE, drawings)
        return jsonify({"success": True})
    else:
        path = request.args.get('path')
        drawings = load_json(DRAWINGS_FILE)
        return jsonify({"drawing": drawings.get(path, "")})
# ==========================================

@app.route('/api/file')
def serve_file_route():
    path = request.args.get('path')
    if not path or not path.startswith(BASE_DIR): return "Access Denied", 403
    try: return send_file(path)
    except Exception as e: return str(e), 404

@app.route('/api/create', methods=['POST'])
def create_folder():
    try: os.makedirs(os.path.join(request.json['path'], request.json['name']), exist_ok=True); return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)})

@app.route('/api/rename', methods=['POST'])
def rename_item():
    try: os.rename(request.json['path'], os.path.join(os.path.dirname(request.json['path']), request.json['new_name'])); return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)})

@app.route('/api/delete', methods=['POST'])
def delete_item():
    p = request.json['path']
    try: shutil.rmtree(p) if os.path.isdir(p) else os.remove(p); return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)})

@app.route('/api/move', methods=['POST'])
def move_item():
    try: shutil.move(request.json['src_path'], request.json['dest_folder']); return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)})

def launch_browser():
    time.sleep(1.5)
    print("\n[System] Server online. Deploying interface to browser...")
    webbrowser.open("http://127.0.0.1:5000/")

if __name__ == '__main__':
    init_base_dir()
    threading.Thread(target=launch_browser, daemon=True).start()
    app.run(debug=True, use_reloader=False)