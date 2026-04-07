from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json

from .config import Settings
from .orchestrator import AgenticOrchestrator


HTML = """<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Agentic Lab Studio</title>
  <style>
    :root { --bg:#0b1020; --card:#131a32; --text:#e6ebff; --muted:#a6b0d8; --accent:#7c9cff; --accent2:#42e3b4; }
    *{box-sizing:border-box} body{margin:0; font-family:Inter,ui-sans-serif,system-ui; background:radial-gradient(1200px 500px at 10% -10%, #2a3b80 0%, transparent 70%), radial-gradient(1000px 600px at 120% 0%, #0f7f73 0%, transparent 55%), var(--bg); color:var(--text);} 
    .wrap{max-width:980px; margin:36px auto; padding:0 16px;} .hero{display:flex; justify-content:space-between; align-items:center; margin-bottom:18px}
    .title{font-size:32px; font-weight:800; letter-spacing:.2px} .subtitle{color:var(--muted)}
    .card{background:linear-gradient(180deg, #151d3a, #10162d); border:1px solid #24305f; border-radius:16px; padding:16px; box-shadow:0 12px 32px rgba(0,0,0,.28)}
    textarea{width:100%; min-height:120px; resize:vertical; color:var(--text); background:#0b1229; border:1px solid #2a3768; border-radius:12px; padding:12px; outline:none}
    button{margin-top:12px; background:linear-gradient(90deg,var(--accent),var(--accent2)); color:#081028; border:0; border-radius:10px; font-weight:700; padding:10px 16px; cursor:pointer}
    .output{white-space:pre-wrap; line-height:1.6; margin-top:16px; background:#0b1229; border:1px solid #2a3768; border-radius:12px; padding:14px; min-height:160px}
    .row{display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px} .small{font-size:13px; color:var(--muted)}
    @media (max-width:760px){ .row{grid-template-columns:1fr;} .title{font-size:26px;} }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"hero\">
      <div>
        <div class=\"title\">Agentic Lab Studio</div>
        <div class=\"subtitle\">规划、技能、工具、记忆 —— 一体化 Agentic 控制台</div>
      </div>
      <div class=\"small\">Optional UI • Localhost</div>
    </div>

    <div class=\"card\">
      <label class=\"small\">任务描述</label>
      <textarea id=\"task\" placeholder=\"例如：分析当前仓库并提出可执行优化方案\"></textarea>
      <div class=\"row\">
        <div>
          <label class=\"small\">显式技能（逗号分隔，可选）</label>
          <textarea id=\"skills\" style=\"min-height:78px\" placeholder=\"coding, research\"></textarea>
        </div>
        <div>
          <label class=\"small\">状态</label>
          <div id=\"status\" class=\"output\" style=\"min-height:78px\">Ready</div>
        </div>
      </div>
      <button onclick=\"runTask()\">运行 Agent</button>
      <div id=\"result\" class=\"output\">结果将在这里显示...</div>
    </div>
  </div>

  <script>
    async function runTask(){
      const task = document.getElementById('task').value.trim();
      const skillText = document.getElementById('skills').value.trim();
      if(!task){ alert('请输入任务'); return; }
      document.getElementById('status').textContent = 'Running...';
      const skills = skillText ? skillText.split(',').map(x=>x.trim()).filter(Boolean) : [];
      const res = await fetch('/api/run', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({task, skills}) });
      const data = await res.json();
      document.getElementById('result').textContent = data.result || data.error || '(empty)';
      document.getElementById('status').textContent = data.status;
    }
  </script>
</body>
</html>
"""


class WebUIHandler(BaseHTTPRequestHandler):
    orchestrator: AgenticOrchestrator | None = None

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._json({"error": "Not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/run":
            self._json({"error": "Not found"}, 404)
            return
        if self.orchestrator is None:
            self._json({"error": "Server not initialized"}, 500)
            return

        size = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(size).decode("utf-8") or "{}")
        task = (data.get("task") or "").strip()
        skills = data.get("skills") or []
        if not task:
            self._json({"status": "error", "error": "task is required"}, 400)
            return
        result = self.orchestrator.run(task, requested_skills=skills)
        self._json({"status": "ok", "result": result})


def serve_ui(settings: Settings, host: str = "127.0.0.1", port: int = 8765) -> None:
    orchestrator = AgenticOrchestrator(settings)
    WebUIHandler.orchestrator = orchestrator
    server = ThreadingHTTPServer((host, port), WebUIHandler)
    print(f"Agentic Lab Studio started: http://{host}:{port}")
    server.serve_forever()
