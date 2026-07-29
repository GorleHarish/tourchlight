"""
Torchlight Web GUI Dashboard Server

Lightweight zero-dependency Python HTTP server providing a modern Web UI
for monitoring Autonomous Harness goals, tasks, continuous memory, and project health.
"""

import http.server
import json
import os
import socketserver
import sys
from pathlib import Path
from typing import Optional

PORT = 8500


def get_dashboard_data(project_root) -> dict:
    root = Path(project_root).resolve()
    torchlight_dir = root / ".torchlight"
    goal_json = torchlight_dir / "goal_spec.json"
    tasks_md = torchlight_dir / "tasks.md"
    mem_file = root / ".context-memory.json"

    data = {
        "project_name": root.name,
        "project_root": str(root),

        "goal": None,
        "tasks": [],
        "memory": {
            "facts": [],
            "arch_decisions": [],
            "tried_and_failed": [],
            "tech_stack": [],
        },
        "has_goal": False,
    }

    if goal_json.exists():
        try:
            with open(goal_json, "r", encoding="utf-8") as f:
                goal_data = json.load(f)
            data["goal"] = goal_data
            data["tasks"] = goal_data.get("tasks", [])
            data["has_goal"] = True
        except Exception:
            pass

    if mem_file.exists():
        try:
            with open(mem_file, "r", encoding="utf-8") as f:
                data["memory"] = json.load(f)
        except Exception:
            pass

    return data


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Torchlight Web Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --accent-blue: #38bdf8;
            --accent-purple: #a855f7;
            --accent-green: #22c55e;
            --accent-yellow: #eab308;
            --accent-red: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --glass-bg: rgba(30, 41, 59, 0.7);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background: var(--glass-bg);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
            padding: 1.25rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 700;
            font-size: 1.35rem;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 1.1rem;
            -webkit-text-fill-color: #fff;
        }

        .project-badge {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 0.4rem 0.9rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }

        main {
            flex: 1;
            padding: 2rem;
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 2rem;
        }

        @media (max-width: 1024px) {
            main {
                grid-template-columns: 1fr;
            }
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            transition: border-color 0.2s ease;
        }

        .card:hover {
            border-color: #475569;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.25rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border-color);
        }

        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .progress-bar-bg {
            background: var(--bg-dark);
            height: 10px;
            border-radius: 5px;
            overflow: hidden;
            margin-top: 0.5rem;
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
            width: 0%;
            transition: width 0.4s ease;
        }

        .task-list {
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
        }

        .task-item {
            background: var(--bg-dark);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            transition: transform 0.15s ease, border-color 0.15s ease;
        }

        .task-item:hover {
            transform: translateY(-2px);
            border-color: var(--accent-blue);
        }

        .task-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .task-id {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--accent-blue);
        }

        .status-badge {
            padding: 0.25rem 0.65rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .status-verified {
            background: rgba(34, 197, 94, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(34, 197, 94, 0.3);
        }

        .status-in_progress {
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-blue);
            border: 1px solid rgba(56, 189, 248, 0.3);
        }

        .status-pending {
            background: rgba(234, 179, 8, 0.15);
            color: var(--accent-yellow);
            border: 1px solid rgba(234, 179, 8, 0.3);
        }

        .status-failed {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .task-desc {
            font-size: 0.95rem;
            color: var(--text-main);
            line-height: 1.4;
        }

        .task-files {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            color: var(--text-muted);
            display: flex;
            gap: 0.4rem;
            flex-wrap: wrap;
        }

        .file-pill {
            background: rgba(255, 255, 255, 0.05);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
        }

        .memory-section {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .memory-block {
            background: var(--bg-dark);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.85rem;
        }

        .memory-block-title {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 0.4rem;
        }

        .memory-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
            font-size: 0.88rem;
        }

        .memory-list li {
            color: var(--text-main);
            word-break: break-word;
        }

        .refresh-btn {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            color: #fff;
            border: none;
            padding: 0.5rem 1.25rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s ease;
        }

        .refresh-btn:hover {
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <header>
        <div class="logo">
            <div class="logo-icon">🔥</div>
            <span>Torchlight Autonomous Dashboard</span>
        </div>
        <div class="project-badge" id="project-badge">Loading...</div>
    </header>

    <main>
        <section style="display: flex; flex-direction: column; gap: 1.5rem;">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <span>🎯 Active Goal</span>
                    </div>
                    <button class="refresh-btn" onclick="fetchData()">Refresh Data</button>
                </div>
                <h2 id="goal-title" style="font-size: 1.3rem; margin-bottom: 0.5rem; color: var(--accent-blue);">Loading Goal...</h2>
                <p id="goal-desc" style="color: var(--text-muted); font-size: 0.95rem; margin-bottom: 1rem;"></p>
                <div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-muted);">
                        <span>Goal Task Progress</span>
                        <span id="progress-text">0 / 0 verified</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" id="progress-fill"></div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <span>📋 Autonomous Task Spec</span>
                    </div>
                </div>
                <div class="task-list" id="task-container">
                    <p style="color: var(--text-muted);">No tasks initialized yet. Run <code>python -m core.execution.run_harness</code> or type <code>/tasks</code> in chat.</p>
                </div>
            </div>
        </section>

        <aside style="display: flex; flex-direction: column; gap: 1.5rem;">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <span>🧠 Continuous Project Memory</span>
                    </div>
                </div>
                <div class="memory-section">
                    <div class="memory-block">
                        <div class="memory-block-title">Key Architectural Decisions</div>
                        <ul class="memory-list" id="mem-arch">
                            <li style="color: var(--text-muted);">None recorded</li>
                        </ul>
                    </div>

                    <div class="memory-block">
                        <div class="memory-block-title">Tried & Failed Approaches</div>
                        <ul class="memory-list" id="mem-failed">
                            <li style="color: var(--text-muted);">None recorded</li>
                        </ul>
                    </div>

                    <div class="memory-block">
                        <div class="memory-block-title">Tech Stack & Tools</div>
                        <ul class="memory-list" id="mem-stack">
                            <li style="color: var(--text-muted);">Python, Tiktoken, AST Engine</li>
                        </ul>
                    </div>
                </div>
            </div>
        </aside>
    </main>

    <script>
        async function fetchData() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();

                document.getElementById('project-badge').innerText = data.project_name;

                if (data.goal) {
                    document.getElementById('goal-title').innerText = data.goal.title || 'Workspace Goal';
                    document.getElementById('goal-desc').innerText = data.goal.description || '';
                    
                    const tasks = data.tasks || [];
                    const verified = tasks.filter(t => t.status === 'verified').length;
                    const pct = tasks.length ? Math.round((verified / tasks.length) * 100) : 0;

                    document.getElementById('progress-text').innerText = `${verified} / ${tasks.length} verified (${pct}%)`;
                    document.getElementById('progress-fill').style.width = `${pct}%`;

                    renderTasks(tasks);
                } else {
                    document.getElementById('goal-title').innerText = 'No Active Goal Spec';
                    document.getElementById('goal-desc').innerText = 'Initialize a goal using /tasks or python -m core.execution.run_harness';
                    document.getElementById('task-container').innerHTML = '<p style="color: var(--text-muted);">No tasks initialized yet.</p>';
                }

                renderMemory(data.memory || {});
            } catch (err) {
                console.error('Failed to fetch dashboard data:', err);
            }
        }

        function renderTasks(tasks) {
            const container = document.getElementById('task-container');
            if (!tasks.length) {
                container.innerHTML = '<p style="color: var(--text-muted);">No tasks found.</p>';
                return;
            }

            container.innerHTML = tasks.map(t => {
                const statusClass = `status-${t.status || 'pending'}`;
                const files = (t.target_files || []).map(f => `<span class="file-pill">${f}</span>`).join('');
                return `
                    <div class="task-item">
                        <div class="task-top">
                            <span class="task-id">${t.id}</span>
                            <span class="status-badge ${statusClass}">${t.status || 'pending'}</span>
                        </div>
                        <div class="task-desc">${t.description}</div>
                        ${files ? `<div class="task-files">${files}</div>` : ''}
                    </div>
                `;
            }).join('');
        }

        function renderMemory(mem) {
            renderList('mem-arch', mem.arch_decisions);
            renderList('mem-failed', mem.tried_and_failed);
            renderList('mem-stack', mem.tech_stack);
        }

        function renderList(elemId, items) {
            const el = document.getElementById(elemId);
            if (items && items.length) {
                el.innerHTML = items.map(i => `<li>• ${i}</li>`).join('');
            } else {
                el.innerHTML = '<li style="color: var(--text-muted);">None recorded</li>';
            }
        }

        fetchData();
        setInterval(fetchData, 5000);
    </script>
</body>
</html>
"""


class DashboardHTTPHandler(http.server.BaseHTTPRequestHandler):
    project_root = Path.cwd()

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif self.path == "/api/data":
            data = get_dashboard_data(self.project_root)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet HTTP logging


def run_dashboard_server(project_root: Optional[Path] = None, port: int = PORT) -> None:
    root = Path(project_root).resolve() if project_root else Path.cwd()
    DashboardHTTPHandler.project_root = root

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), DashboardHTTPHandler) as httpd:
        print(f"🔥 Torchlight Web Dashboard running at: http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard server stopped.")


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else PORT
    run_dashboard_server(port=p)
