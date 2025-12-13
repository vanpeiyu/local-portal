from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import socket
import json
import subprocess
import os
from typing import List, Dict
import asyncio
import httpx
from bs4 import BeautifulSoup
import base64
from playwright.async_api import async_playwright

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

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

def get_process_info(port: int) -> tuple:
    try:
        result = subprocess.run(
            ['lsof', '-i', f':{port}', '-sTCP:LISTEN', '-n', '-P'],
            capture_output=True, text=True, timeout=1
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            process = parts[0] if parts else "Unknown"
            
            non_web_processes = {'postgres', 'mysql', 'mysqld', 'mongod', 'redis-server', 'memcached'}
            is_non_web = any(nwp in process.lower() for nwp in non_web_processes)
            return process, not is_non_web
    except:
        pass
    return "Unknown", True

async def get_page_info(port: int) -> tuple:
    try:
        async with httpx.AsyncClient(timeout=0.5) as client:
            response = await client.get(f"http://localhost:{port}")
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find('title')
            title_text = title.string.strip() if title and title.string else None
            
            if not title_text:
                return None, None
            
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page(viewport={'width': 1280, 'height': 720})
                await page.goto(f"http://localhost:{port}", timeout=5000, wait_until='load')
                await page.wait_for_timeout(500)
                screenshot = await page.screenshot(type='png')
                await browser.close()
                thumbnail = base64.b64encode(screenshot).decode('utf-8')
                return title_text, thumbnail
    except:
        return None, None

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/ports")
async def get_ports():
    ports = await scan_ports()
    ports = [p for p in ports if p["port"] != 8888]
    for p in ports:
        p["process"], is_likely_web = get_process_info(p["port"])
        if is_likely_web:
            p["title"], p["thumbnail"] = await get_page_info(p["port"])
        else:
            p["title"], p["thumbnail"] = None, None
    return {"ports": ports}

@app.post("/api/control/stop")
async def stop_service():
    plist_path = f"{os.path.expanduser('~')}/Library/LaunchAgents/com.localportal.plist"
    domain = f"gui/{os.getuid()}"
    
    def execute_in_background():
        import time
        time.sleep(0.5)
        subprocess.run(['launchctl', 'bootout', domain, plist_path], capture_output=True)
    
    import threading
    thread = threading.Thread(target=execute_in_background, daemon=True)
    thread.start()
    return JSONResponse({"success": True})

@app.get("/api/ports/stream")
async def stream_ports(existing: str = ""):
    async def generate():
        existing_ports = set(map(int, existing.split(','))) if existing else set()
        ports = await scan_ports()
        ports = [p for p in ports if p["port"] != 8888]
        
        # 新しいポートを優先、既存ポートは後回し
        new_ports = [p for p in ports if p["port"] not in existing_ports]
        old_ports = [p for p in ports if p["port"] in existing_ports]
        sorted_ports = new_ports + old_ports
        
        for p in sorted_ports:
            p["process"], is_likely_web = get_process_info(p["port"])
            if is_likely_web:
                p["title"], p["thumbnail"] = await get_page_info(p["port"])
            else:
                p["title"], p["thumbnail"] = None, None
            yield f"data: {json.dumps(p)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local Portal</title>
    <link rel="icon" href="/static/favicon.png" type="image/png">
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
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--border);
            position: relative;
        }
        .status-bar {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
            color: var(--text-secondary);
        }
        .status-bar.scanning {
            border-color: var(--accent);
            background: linear-gradient(90deg, var(--bg-card), var(--bg-secondary), var(--bg-card));
            background-size: 200% 100%;
            animation: scanning 2s linear infinite;
        }
        .status-bar.complete {
            border-color: var(--border);
            color: var(--text-secondary);
            opacity: 0.6;
        }
        .status-bar.complete .spinner {
            display: none;
        }
        .status-bar.stopping {
            border-color: #ef4444;
            background: linear-gradient(90deg, var(--bg-card), var(--bg-secondary), var(--bg-card));
            background-size: 200% 100%;
            animation: scanning 2s linear infinite;
            color: #ef4444;
        }
        .status-bar.stopped {
            border-color: #ef4444;
            color: #ef4444;
            background: var(--bg-card);
        }
        .status-bar.stopped .spinner {
            display: none;
        }

        @keyframes scanning {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
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
        .btn-primary:hover:not(:disabled) {
            background: var(--accent-hover);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px var(--shadow);
        }
        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .btn-secondary {
            background: var(--bg-card);
            color: var(--text);
            border: 1px solid var(--border);
        }
        .btn-secondary:hover {
            background: var(--bg-secondary);
        }
        .btn-icon {
            background: var(--bg-card);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 10px;
        }
        .btn-icon:hover:not(:disabled) {
            background: var(--bg-secondary);
        }
        .btn-icon:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .btn-stop {
            padding: 6px 12px;
            background: transparent;
            color: var(--text-secondary);
            border: 1px solid transparent;
            font-size: 12px;
            opacity: 0.3;
        }
        .btn-stop:hover {
            opacity: 1;
            border-color: var(--border);
            background: var(--bg-secondary);
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal.show {
            display: flex;
        }
        .modal-content {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 24px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 8px 32px var(--shadow);
        }
        .modal-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 12px;
            color: var(--text);
        }
        .modal-body {
            color: var(--text-secondary);
            margin-bottom: 20px;
            line-height: 1.6;
        }
        .modal-actions {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }
        .stopped-message {
            text-align: center;
            padding: 40px 20px;
        }
        .stopped-message h2 {
            font-size: 24px;
            margin-bottom: 16px;
            color: var(--text);
        }
        .stopped-message p {
            color: var(--text-secondary);
            margin-bottom: 24px;
        }
        .cmd-wrapper {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
        }
        .cmd-display {
            flex: 1;
            background: var(--bg-secondary);
            padding: 12px 16px;
            border-radius: 8px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            color: var(--accent);
            word-break: break-all;
        }
        .btn-copy {
            padding: 12px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-copy:hover {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
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
        .skeleton {
            background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--border) 50%, var(--bg-secondary) 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: 6px;
        }
        @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        .skeleton-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px var(--shadow);
        }
        .skeleton-thumbnail {
            width: 100%;
            height: 180px;
            background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--border) 50%, var(--bg-secondary) 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
        }
        .skeleton-body {
            padding: 20px;
        }
        .skeleton-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 12px;
        }
        .skeleton-badge {
            width: 60px;
            height: 32px;
        }
        .skeleton-process {
            width: 80px;
            height: 24px;
        }
        .skeleton-title {
            width: 70%;
            height: 20px;
            margin-bottom: 8px;
        }
        .skeleton-link {
            width: 90%;
            height: 16px;
        }
        .grid {
            display: grid;
            gap: 16px;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
        }
        .portal-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 16px;
            color: inherit;
            opacity: 0.6;
            pointer-events: none;
        }
        .portal-icon {
            font-size: 48px;
            background: linear-gradient(135deg, var(--accent), #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            opacity: 0.5;
        }
        .portal-info {
            flex: 1;
        }
        .portal-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }
        .portal-meta {
            font-size: 12px;
            color: var(--text-secondary);
            opacity: 0.7;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.2s;
            box-shadow: 0 2px 8px var(--shadow);
            cursor: pointer;
            text-decoration: none;
            display: block;
            color: inherit;
        }
        .card-thumbnail {
            width: 100%;
            height: 180px;
            object-fit: cover;
            background: var(--bg-secondary);
        }
        .card-body {
            padding: 20px;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px var(--shadow);
            border-color: var(--accent);
        }
        .card:hover .card-thumbnail {
            opacity: 0.9;
        }
        .card.checking {
            opacity: 0.5;
            pointer-events: none;
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
        .section-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin: 32px 0 16px 0;
            color: var(--text);
        }
        .non-web-table {
            width: 100%;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px var(--shadow);
        }
        .non-web-table table {
            width: 100%;
            border-collapse: collapse;
        }
        .non-web-table th {
            background: var(--bg-secondary);
            padding: 12px 16px;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .non-web-table th:first-child,
        .non-web-table td:first-child {
            text-align: right;
        }
        .non-web-table th:last-child,
        .non-web-table td:last-child {
            text-align: left;
        }
        .non-web-table td {
            padding: 12px 16px;
            border-top: 1px solid var(--border);
            font-size: 14px;
            color: var(--text);
        }
        .non-web-table tr:hover {
            background: var(--bg-secondary);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div style="display: flex; align-items: center; gap: 20px;">
                <h1>🚀 Local Portal</h1>
                <button class="btn-stop" onclick="confirmStop()">⏹️ 停止</button>
            </div>
            <div class="controls">
                <button class="btn-primary" id="refreshBtn" onclick="refresh()">🔄 更新</button>
                <button class="btn-icon" id="themeBtn" onclick="toggleTheme()" title="テーマ切替">🌓</button>
            </div>
        </header>
        <div class="modal" id="modal" onclick="closeModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-title" id="modalTitle"></div>
                <div class="modal-body" id="modalBody"></div>
                <div class="modal-actions">
                    <button class="btn-secondary" onclick="closeModal()">キャンセル</button>
                    <button class="btn-primary" onclick="executeAction()" id="confirmBtn">実行</button>
                </div>
            </div>
        </div>
        <div id="status" class="status-bar scanning">
            <div class="spinner"></div>
            <span id="statusText">ポートスキャン中...</span>
        </div>
        <div id="content"></div>
    </div>
    <script>
        function confirmStop() {
            const modal = document.getElementById('modal');
            document.getElementById('modalTitle').textContent = 'サービスを停止しますか？';
            document.getElementById('modalBody').textContent = 'Local Portalが停止します。再度起動するにはターミナルでコマンドを実行する必要があります。';
            modal.classList.add('show');
        }
        
        function closeModal() {
            document.getElementById('modal').classList.remove('show');
        }
        
        async function executeAction() {
            closeModal();
            
            const statusBar = document.getElementById('status');
            const statusText = document.getElementById('statusText');
            statusBar.className = 'status-bar stopping';
            statusText.textContent = 'サービスを停止しています...';
            
            await fetch('/api/control/stop', { method: 'POST' });
            setTimeout(() => showStopped(), 1000);
        }
        
        function showStopped() {
            document.getElementById('refreshBtn').disabled = true;
            document.getElementById('themeBtn').disabled = true;
            
            const statusBar = document.getElementById('status');
            const statusText = document.getElementById('statusText');
            statusBar.className = 'status-bar stopped';
            statusText.textContent = '⏹️ サービスを停止しました';
            
            const cmd = 'launchctl load ~/Library/LaunchAgents/com.localportal.plist';
            document.getElementById('content').innerHTML = `
                <div class="stopped-message">
                    <h2>再起動方法</h2>
                    <p>以下のコマンドをターミナルで実行してください。</p>
                    <div class="cmd-wrapper">
                        <div class="cmd-display">${cmd}</div>
                        <button class="btn-copy" onclick="navigator.clipboard.writeText('${cmd}')" title="コピー">📋</button>
                    </div>
                </div>
            `;
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
        
        function showSkeleton() {
            const skeletonHTML = `
                <h2 class="section-title">🌐 Webサーバー</h2>
                <div id="web-grid" class="grid">
                    <div class="portal-card">
                        <div class="portal-icon">🚀</div>
                        <div class="portal-info">
                            <div class="portal-title">Local Portal</div>
                            <div class="portal-meta">Port 8888 · uvicorn</div>
                        </div>
                    </div>
                    ${Array(3).fill(0).map(() => `
                        <div class="skeleton-card">
                            <div class="skeleton-thumbnail"></div>
                            <div class="skeleton-body">
                                <div class="skeleton-header">
                                    <div class="skeleton skeleton-badge"></div>
                                    <div class="skeleton skeleton-process"></div>
                                </div>
                                <div class="skeleton skeleton-title"></div>
                                <div class="skeleton skeleton-link"></div>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <h2 class="section-title">🔌 その他のサービス</h2>
                <div id="non-web-table" class="non-web-table"><table><thead><tr><th>ポート</th><th>プロセス</th></tr></thead><tbody></tbody></table></div>
            `;
            document.getElementById('content').innerHTML = skeletonHTML;
        }
        
        let currentPorts = new Set();
        let statusTimeout = null;
        
        async function refresh() {
            const existingPorts = Array.from(currentPorts).join(',');
            const isFirstLoad = currentPorts.size === 0;
            
            // ステータス更新
            const statusBar = document.getElementById('status');
            const statusText = document.getElementById('statusText');
            statusBar.className = 'status-bar scanning';
            statusText.textContent = 'ポートスキャン中...';
            
            if (isFirstLoad) {
                showSkeleton();
            } else {
                // セクションタイトルを更新中表示に
                const webTitle = document.querySelector('.section-title');
                const nonWebTitle = document.querySelectorAll('.section-title')[1];
                if (webTitle) webTitle.textContent = '🌐 Webサーバー (更新中...)';
                if (nonWebTitle) nonWebTitle.textContent = '🔌 その他のサービス (更新中...)';
                // 既存カードを確認中状態にする
                document.querySelectorAll('.card').forEach(card => card.classList.add('checking'));
                document.querySelectorAll('#non-web-table tbody tr').forEach(row => row.style.opacity = '0.5');
            }
            
            const newPorts = new Set();
            const webPorts = [];
            const nonWebPorts = [];
            
            const eventSource = new EventSource(`/api/ports/stream?existing=${existingPorts}`);
            
            eventSource.onmessage = (event) => {
                if (event.data === '[DONE]') {
                    eventSource.close();
                    
                    // 消えたポートのカードを削除
                    document.querySelectorAll('.card:not(.portal-card)').forEach(card => {
                        const port = parseInt(card.dataset.port);
                        if (!newPorts.has(port)) {
                            card.remove();
                        }
                    });
                    document.querySelectorAll('#non-web-table tbody tr').forEach(row => {
                        const port = parseInt(row.dataset.port);
                        if (!newPorts.has(port)) {
                            row.remove();
                        } else {
                            row.style.opacity = '1';
                        }
                    });
                    
                    currentPorts = newPorts;
                    
                    // ステータス更新
                    statusBar.className = 'status-bar complete';
                    statusText.textContent = `✓ スキャン完了 (Webサーバー: ${webPorts.length}個、その他: ${nonWebPorts.length}個)`;
                    
                    // セクションタイトル更新
                    const webTitle = document.querySelector('.section-title');
                    const nonWebTitle = document.querySelectorAll('.section-title')[1];
                    if (webTitle) webTitle.textContent = `🌐 Webサーバー (${webPorts.length})`;
                    if (nonWebTitle) nonWebTitle.textContent = `🔌 その他のサービス (${nonWebPorts.length})`;
                    
                    if (webPorts.length === 0 && nonWebPorts.length === 0) {
                        document.getElementById('content').innerHTML = `
                            <h2 class="section-title">🌐 Webサーバー</h2>
                            <div id="web-grid" class="grid">
                                <div class="portal-card">
                                    <div class="portal-icon">🚀</div>
                                    <div class="portal-info">
                                        <div class="portal-title">Local Portal</div>
                                        <div class="portal-meta">Port 8888 · uvicorn</div>
                                    </div>
                                </div>
                            </div>
                            <div class="empty">📭 他に開いているポートが見つかりませんでした</div>
                        `;
                    }
                    return;
                }
                
                // ステータス更新（検出中）
                statusText.textContent = `ポートスキャン中... (Webサーバー: ${webPorts.length}個、その他: ${nonWebPorts.length}個)`;
                
                const port = JSON.parse(event.data);
                const isNewPort = !currentPorts.has(port.port);
                newPorts.add(port.port);
                
                if (port.title) {
                    webPorts.push(port);
                    renderWebPort(port);
                    // 新規ポートの場合、ステータスに表示
                    if (isNewPort) {
                        if (statusTimeout) clearTimeout(statusTimeout);
                        statusText.textContent = `✨ 新規ポート検出: ${port.port} (${port.process})`;
                        statusTimeout = setTimeout(() => {
                            if (statusBar.className === 'status-bar scanning') {
                                statusText.textContent = 'ポートスキャン中...';
                            }
                        }, 2000);
                    }
                } else {
                    nonWebPorts.push(port);
                    renderNonWebPort(port);
                    // 新規ポートの場合、ステータスに表示
                    if (isNewPort) {
                        if (statusTimeout) clearTimeout(statusTimeout);
                        statusText.textContent = `✨ 新規ポート検出: ${port.port} (${port.process})`;
                        statusTimeout = setTimeout(() => {
                            if (statusBar.className === 'status-bar scanning') {
                                statusText.textContent = 'ポートスキャン中...';
                            }
                        }, 2000);
                    }
                }
            };
            
            eventSource.onerror = () => {
                eventSource.close();
            };
        }
        
        function renderWebPort(p) {
            const grid = document.getElementById('web-grid');
            if (grid.querySelector('.skeleton-card')) {
                grid.innerHTML = `
                    <div class="portal-card">
                        <div class="portal-icon">🚀</div>
                        <div class="portal-info">
                            <div class="portal-title">Local Portal</div>
                            <div class="portal-meta">Port 8888 · uvicorn</div>
                        </div>
                    </div>
                `;
            }
            
            // 既存カードを更新または新規作成
            let card = grid.querySelector(`[data-port="${p.port}"]`);
            const title = p.title || 'Untitled';
            const thumbnail = p.thumbnail ? `<img class="card-thumbnail" src="data:image/png;base64,${p.thumbnail}" alt="${title}">` : '';
            
            if (card) {
                card.classList.remove('checking');
                card.innerHTML = `
                    ${thumbnail}
                    <div class="card-body">
                        <div class="card-header">
                            <span class="port-badge">${p.port}</span>
                            <span class="process-badge">${p.process}</span>
                        </div>
                        <div class="card-title">${title}</div>
                        <div class="card-link">http://${window.location.hostname}:${p.port}</div>
                    </div>
                `;
            } else {
                card = document.createElement('a');
                card.className = 'card';
                card.dataset.port = p.port;
                card.href = `http://${window.location.hostname}:${p.port}`;
                card.target = '_blank';
                card.innerHTML = `
                    ${thumbnail}
                    <div class="card-body">
                        <div class="card-header">
                            <span class="port-badge">${p.port}</span>
                            <span class="process-badge">${p.process}</span>
                        </div>
                        <div class="card-title">${title}</div>
                        <div class="card-link">http://${window.location.hostname}:${p.port}</div>
                    </div>
                `;
                
                // ポート番号順に挿入
                const cards = Array.from(grid.querySelectorAll('.card'));
                const insertIndex = cards.findIndex(c => parseInt(c.dataset.port) > p.port);
                if (insertIndex === -1) {
                    grid.appendChild(card);
                } else {
                    grid.insertBefore(card, cards[insertIndex]);
                }
            }
        }
        
        function renderNonWebPort(p) {
            const tbody = document.querySelector('#non-web-table tbody');
            let row = tbody.querySelector(`[data-port="${p.port}"]`);
            
            if (row) {
                row.style.opacity = '1';
                row.innerHTML = `<td>${p.port}</td><td>${p.process}</td>`;
            } else {
                row = document.createElement('tr');
                row.dataset.port = p.port;
                row.innerHTML = `<td>${p.port}</td><td>${p.process}</td>`;
                
                // ポート番号順に挿入
                const rows = Array.from(tbody.querySelectorAll('tr'));
                const insertIndex = rows.findIndex(r => parseInt(r.dataset.port) > p.port);
                if (insertIndex === -1) {
                    tbody.appendChild(row);
                } else {
                    tbody.insertBefore(row, rows[insertIndex]);
                }
            }
        }
        

        
        initTheme();
        refresh();
    </script>
</body>
</html>
"""
