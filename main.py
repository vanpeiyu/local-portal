from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import socket
import subprocess
from typing import List, Dict
import asyncio
import httpx
from bs4 import BeautifulSoup

app = FastAPI()

async def check_port(port: int) -> Dict:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    try:
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            return {"port": port, "status": "open"}
    except:
        pass
    finally:
        sock.close()
    return None

async def scan_ports(start: int = 3000, end: int = 9999) -> List[Dict]:
    tasks = [check_port(port) for port in range(start, end + 1)]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r]

def get_process_info(port: int) -> str:
    try:
        result = subprocess.run(
            ['lsof', '-i', f':{port}', '-sTCP:LISTEN', '-n', '-P'],
            capture_output=True, text=True, timeout=1
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            return parts[0] if parts else "Unknown"
    except:
        pass
    return "Unknown"

async def get_page_title(port: int) -> str:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"http://localhost:{port}")
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find('title')
            return title.string.strip() if title and title.string else None
    except:
        return None

@app.get("/api/ports")
async def get_ports():
    ports = await scan_ports()
    for p in ports:
        p["process"] = get_process_info(p["port"])
        p["title"] = await get_page_title(p["port"])
    return {"ports": ports}

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local Portal</title>
    <style>
        :root {
            --bg: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-card: #ffffff;
            --text: #1a1a1a;
            --text-secondary: #6c757d;
            --border: #e9ecef;
            --shadow: rgba(0,0,0,0.1);
            --accent: #6366f1;
            --accent-hover: #4f46e5;
        }
        [data-theme="dark"] {
            --bg: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --text: #f1f5f9;
            --text-secondary: #94a3b8;
            --border: #334155;
            --shadow: rgba(0,0,0,0.3);
            --accent: #818cf8;
            --accent-hover: #6366f1;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg);
            color: var(--text);
            transition: background 0.3s, color 0.3s;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--border);
        }
        h1 {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent), #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .controls {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .btn-primary {
            background: var(--accent);
            color: white;
        }
        .btn-primary:hover {
            background: var(--accent-hover);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px var(--shadow);
        }
        .btn-icon {
            background: var(--bg-card);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 10px;
        }
        .btn-icon:hover {
            background: var(--bg-secondary);
        }
        .info-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px var(--shadow);
        }
        .info-card h3 {
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .cmd-item {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }
        .cmd-label {
            min-width: 80px;
            font-size: 13px;
            font-weight: 500;
            color: var(--text);
        }
        .cmd-wrapper {
            flex: 1;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .cmd-code {
            flex: 1;
            background: var(--bg-secondary);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-family: 'Monaco', 'Courier New', monospace;
            color: var(--accent);
        }
        .btn-copy {
            padding: 6px 10px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-copy:hover {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }
        .loading {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-secondary);
            font-size: 16px;
        }
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 10px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .grid {
            display: grid;
            gap: 16px;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.2s;
            box-shadow: 0 2px 8px var(--shadow);
            cursor: pointer;
            text-decoration: none;
            display: block;
            color: inherit;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px var(--shadow);
            border-color: var(--accent);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .port-badge {
            background: var(--accent);
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 18px;
        }
        .process-badge {
            background: var(--bg-secondary);
            color: var(--text-secondary);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
        }
        .card-title {
            color: var(--text);
            font-size: 15px;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .card-link {
            color: var(--accent);
            text-decoration: none;
            font-size: 14px;
            word-break: break-all;
        }
        .card-link:hover {
            text-decoration: underline;
        }
        .empty {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-secondary);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 Local Portal</h1>
            <div class="controls">
                <button class="btn-primary" onclick="refresh()">🔄 更新</button>
                <button class="btn-icon" onclick="toggleTheme()" title="テーマ切替">🌓</button>
            </div>
        </header>
        <div class="info-card">
            <h3>管理コマンド</h3>
            <div class="cmd-item">
                <div class="cmd-label">停止:</div>
                <div class="cmd-wrapper">
                    <div class="cmd-code">launchctl unload ~/Library/LaunchAgents/com.localportal.plist</div>
                    <button class="btn-copy" onclick="copyCmd('launchctl unload ~/Library/LaunchAgents/com.localportal.plist')">📋</button>
                </div>
            </div>
            <div class="cmd-item">
                <div class="cmd-label">起動:</div>
                <div class="cmd-wrapper">
                    <div class="cmd-code">launchctl load ~/Library/LaunchAgents/com.localportal.plist</div>
                    <button class="btn-copy" onclick="copyCmd('launchctl load ~/Library/LaunchAgents/com.localportal.plist')">📋</button>
                </div>
            </div>
            <div class="cmd-item">
                <div class="cmd-label">再起動:</div>
                <div class="cmd-wrapper">
                    <div class="cmd-code">launchctl unload ~/Library/LaunchAgents/com.localportal.plist && launchctl load ~/Library/LaunchAgents/com.localportal.plist</div>
                    <button class="btn-copy" onclick="copyCmd('launchctl unload ~/Library/LaunchAgents/com.localportal.plist && launchctl load ~/Library/LaunchAgents/com.localportal.plist')">📋</button>
                </div>
            </div>
        </div>
        <div id="content" class="loading">
            <div class="spinner"></div>スキャン中...
        </div>
    </div>
    <script>
        function copyCmd(text) {
            navigator.clipboard.writeText(text);
        }
        
        function toggleTheme() {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        }
        
        function initTheme() {
            const saved = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = saved || (prefersDark ? 'dark' : 'light');
            document.documentElement.setAttribute('data-theme', theme);
        }
        
        async function refresh() {
            document.getElementById('content').innerHTML = '<div class="loading"><div class="spinner"></div>スキャン中...</div>';
            const res = await fetch('/api/ports');
            const data = await res.json();
            const ports = data.ports;
            
            if (ports.length === 0) {
                document.getElementById('content').innerHTML = '<div class="empty">📭 開いているポートが見つかりませんでした</div>';
                return;
            }
            
            let html = '<div class="grid">';
            ports.forEach(p => {
                const title = p.title || 'Untitled';
                html += `
                    <a class="card" href="http://localhost:${p.port}" target="_blank">
                        <div class="card-header">
                            <span class="port-badge">${p.port}</span>
                            <span class="process-badge">${p.process}</span>
                        </div>
                        <div class="card-title">${title}</div>
                        <div class="card-link">
                            http://localhost:${p.port}
                        </div>
                    </a>
                `;
            });
            html += '</div>';
            document.getElementById('content').innerHTML = html;
        }
        
        initTheme();
        refresh();
    </script>
</body>
</html>
"""
