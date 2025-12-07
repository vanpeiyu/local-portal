from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import socket
import subprocess
from typing import List, Dict
import asyncio

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

@app.get("/api/ports")
async def get_ports():
    ports = await scan_ports()
    for p in ports:
        p["process"] = get_process_info(p["port"])
    return {"ports": ports}

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Local Portal</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        .loading { color: #666; }
        .info { background: #f0f0f0; padding: 12px; border-radius: 4px; margin: 20px 0; font-size: 13px; }
        .info code { background: #fff; padding: 2px 6px; border-radius: 3px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f5f5f5; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
        button { padding: 8px 16px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Local Portal</h1>
    <div class="info">
        停止: <code>launchctl unload ~/Library/LaunchAgents/com.localportal.plist</code><br>
        起動: <code>launchctl load ~/Library/LaunchAgents/com.localportal.plist</code>
    </div>
    <button onclick="refresh()">更新</button>
    <div id="content" class="loading">スキャン中...</div>
    <script>
        async function refresh() {
            document.getElementById('content').innerHTML = '<p class="loading">スキャン中...</p>';
            const res = await fetch('/api/ports');
            const data = await res.json();
            const ports = data.ports;
            if (ports.length === 0) {
                document.getElementById('content').innerHTML = '<p>開いているポートが見つかりませんでした</p>';
                return;
            }
            let html = '<table><tr><th>ポート</th><th>URL</th><th>プロセス</th></tr>';
            ports.forEach(p => {
                html += `<tr>
                    <td>${p.port}</td>
                    <td><a href="http://localhost:${p.port}" target="_blank">http://localhost:${p.port}</a></td>
                    <td>${p.process}</td>
                </tr>`;
            });
            html += '</table>';
            document.getElementById('content').innerHTML = html;
        }
        refresh();
    </script>
</body>
</html>
"""
