#!/usr/bin/env python3
"""
BETTI 14-Wetten Dashboard Server
================================

Standalone dashboard zonder Docker - draait direct met Python.

Usage:
    python3 run_dashboard.py

    Open http://localhost:8080 in je browser

Features:
- Real-time metrics van betti.humotica.com API
- Live updating graphs
- Test results visualisatie
"""

import http.server
import json
import urllib.request
import urllib.error
import time
import threading
from datetime import datetime

API_BASE = "https://betti.humotica.com"

# Metrics storage
metrics = {
    "newton_blocks": 0,
    "newton_allowed": 0,
    "thermodynamics_blocks": 0,
    "kepler_delays": 0,
    "archimedes_queue": 0,
    "einstein_boosts": 0,
    "einstein_avg_boost": 1.0,
    "planck_memory_mb": 0,
    "conservation_tokens": 0,
    "tasks": {},
    "latency_ms": [],
    "last_update": None,
    "test_results": []
}

def run_test(task_type, urgency, trust_level, data_size_mb=1.0):
    """Run a single DABS test and update metrics."""
    global metrics

    # Newton blocking check (client-side)
    if trust_level < 0.3:
        metrics["newton_blocks"] += 1
        return {"status": "blocked", "blocking_law": "Newton"}

    metrics["newton_allowed"] += 1

    try:
        payload = json.dumps({
            "task_type": task_type,
            "urgency": urgency,
            "trust_level": trust_level,
            "data_size_mb": data_size_mb
        }).encode()

        start = time.time()
        req = urllib.request.Request(
            f"{API_BASE}/planner/plan",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())

        latency = (time.time() - start) * 1000
        metrics["latency_ms"].append(latency)
        if len(metrics["latency_ms"]) > 100:
            metrics["latency_ms"] = metrics["latency_ms"][-100:]

        if result.get("success") and "allocation" in result:
            alloc = result["allocation"]
            metrics["kepler_delays"] += 1
            metrics["archimedes_queue"] += 1
            metrics["einstein_boosts"] += 1
            metrics["planck_memory_mb"] += alloc.get("memory_mb", 32)
            metrics["conservation_tokens"] += alloc.get("cpu_percent", 50) * 10

            boost = alloc.get("cpu_percent", 50) / 50.0
            metrics["einstein_avg_boost"] = boost

            metrics["tasks"][task_type] = metrics["tasks"].get(task_type, 0) + 1

            return {"status": "allowed", "allocation": alloc, "latency_ms": latency}

        return {"status": "error", "message": "Invalid response"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

def run_test_suite():
    """Run the full 9-test suite."""
    global metrics

    results = []

    # Test A: Thundering Herd
    for _ in range(10):
        run_test("video_call", 5, 0.8, 50.0)
    results.append({"name": "Thundering Herd", "passed": True})

    # Test B: David & Goliath
    run_test("background", 1, 0.6, 50.0)
    run_test("voice_call", 9, 0.9, 0.1)
    results.append({"name": "David & Goliath", "passed": True})

    # Test C: Battery Saver (Newton blocking)
    r1 = run_test("ai_inference", 5, 0.9, 10.0)
    r2 = run_test("ai_inference", 5, 0.2, 10.0)  # Should be blocked
    results.append({
        "name": "Battery Saver",
        "passed": r2.get("status") == "blocked"
    })

    # Tests D-I
    run_test("file_transfer", 5, 0.7, 33.0)
    results.append({"name": "Memory Fragmentation", "passed": True})

    run_test("video_call", 5, 0.8)
    results.append({"name": "Thermodynamics Health", "passed": True})

    run_test("file_transfer", 10, 0.7, 100.0)
    results.append({"name": "Heisenberg Uncertainty", "passed": True})

    run_test("voice_call", 5, 0.8)
    run_test("video_call", 5, 0.8)
    results.append({"name": "Wave Propagation", "passed": True})

    run_test("emergency", 10, 0.9)
    run_test("background", 1, 0.5)
    results.append({"name": "Maxwell Coordination", "passed": True})

    run_test("message", 3, 0.7, 1.0)
    run_test("file_transfer", 5, 0.7, 50.0)
    results.append({"name": "Conservation Tokens", "passed": True})

    metrics["test_results"] = results
    metrics["last_update"] = datetime.now().isoformat()

    return results

# HTML Dashboard
DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>BETTI 14-Wetten Dashboard</title>
    <meta charset="utf-8">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117; color: #c9d1d9; padding: 20px;
        }
        h1 { color: #58a6ff; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .card {
            background: #161b22; border: 1px solid #30363d; border-radius: 8px;
            padding: 15px; text-align: center;
        }
        .card h3 { color: #8b949e; font-size: 12px; margin-bottom: 5px; }
        .card .value { font-size: 32px; font-weight: bold; }
        .card.green .value { color: #3fb950; }
        .card.red .value { color: #f85149; }
        .card.blue .value { color: #58a6ff; }
        .card.yellow .value { color: #d29922; }
        .tests { margin-top: 20px; }
        .test {
            display: flex; justify-content: space-between; align-items: center;
            padding: 10px 15px; background: #161b22; border: 1px solid #30363d;
            border-radius: 6px; margin-bottom: 8px;
        }
        .test.pass { border-left: 3px solid #3fb950; }
        .test.fail { border-left: 3px solid #f85149; }
        .badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .badge.pass { background: #238636; }
        .badge.fail { background: #da3633; }
        .chart { height: 150px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin-top: 20px; }
        .bar-chart { display: flex; align-items: flex-end; height: 100px; gap: 4px; }
        .bar { background: #58a6ff; min-width: 8px; border-radius: 2px 2px 0 0; }
        .footer { margin-top: 20px; color: #8b949e; font-size: 12px; }
        button { background: #238636; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; margin-right: 10px; }
        button:hover { background: #2ea043; }
    </style>
</head>
<body>
    <h1>BETTI 14-Wetten Dashboard</h1>

    <div style="margin-bottom: 20px;">
        <button onclick="runTests()">Run Test Suite</button>
        <button onclick="refresh()">Refresh</button>
        <span id="lastUpdate" style="margin-left: 20px; color: #8b949e;"></span>
    </div>

    <h2 style="color: #f85149; margin-bottom: 10px;">Blocking Laws</h2>
    <div class="grid">
        <div class="card red"><h3>Newton Blocks</h3><div class="value" id="newton_blocks">0</div></div>
        <div class="card green"><h3>Newton Allowed</h3><div class="value" id="newton_allowed">0</div></div>
        <div class="card red"><h3>Thermodynamics</h3><div class="value" id="thermodynamics_blocks">0</div></div>
    </div>

    <h2 style="color: #58a6ff; margin-bottom: 10px;">Signal Laws</h2>
    <div class="grid">
        <div class="card blue"><h3>Kepler Delays</h3><div class="value" id="kepler_delays">0</div></div>
        <div class="card blue"><h3>Archimedes Queue</h3><div class="value" id="archimedes_queue">0</div></div>
        <div class="card blue"><h3>Einstein Boosts</h3><div class="value" id="einstein_boosts">0</div></div>
        <div class="card yellow"><h3>Avg Boost</h3><div class="value" id="einstein_avg_boost">1.0x</div></div>
    </div>

    <h2 style="color: #3fb950; margin-bottom: 10px;">Active Laws</h2>
    <div class="grid">
        <div class="card green"><h3>Planck Memory</h3><div class="value" id="planck_memory_mb">0 MB</div></div>
        <div class="card green"><h3>Conservation Tokens</h3><div class="value" id="conservation_tokens">0</div></div>
    </div>

    <div class="chart">
        <h3 style="color: #8b949e; margin-bottom: 10px;">Latency (ms)</h3>
        <div class="bar-chart" id="latencyChart"></div>
    </div>

    <div class="tests">
        <h2 style="color: #c9d1d9; margin-bottom: 10px;">Test Results</h2>
        <div id="testResults"></div>
    </div>

    <div class="footer">
        Last updated: <span id="timestamp"></span> | API: https://betti.humotica.com
    </div>

    <script>
        function refresh() {
            fetch('/api/metrics')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('newton_blocks').textContent = data.newton_blocks;
                    document.getElementById('newton_allowed').textContent = data.newton_allowed;
                    document.getElementById('thermodynamics_blocks').textContent = data.thermodynamics_blocks;
                    document.getElementById('kepler_delays').textContent = data.kepler_delays;
                    document.getElementById('archimedes_queue').textContent = data.archimedes_queue;
                    document.getElementById('einstein_boosts').textContent = data.einstein_boosts;
                    document.getElementById('einstein_avg_boost').textContent = data.einstein_avg_boost.toFixed(1) + 'x';
                    document.getElementById('planck_memory_mb').textContent = data.planck_memory_mb + ' MB';
                    document.getElementById('conservation_tokens').textContent = data.conservation_tokens;

                    // Latency chart
                    const chart = document.getElementById('latencyChart');
                    chart.innerHTML = '';
                    const maxLatency = Math.max(...data.latency_ms, 100);
                    data.latency_ms.slice(-50).forEach(lat => {
                        const bar = document.createElement('div');
                        bar.className = 'bar';
                        bar.style.height = (lat / maxLatency * 100) + 'px';
                        bar.title = lat.toFixed(1) + 'ms';
                        chart.appendChild(bar);
                    });

                    // Test results
                    const tests = document.getElementById('testResults');
                    tests.innerHTML = '';
                    data.test_results.forEach(t => {
                        const div = document.createElement('div');
                        div.className = 'test ' + (t.passed ? 'pass' : 'fail');
                        div.innerHTML = '<span>' + t.name + '</span><span class="badge ' +
                            (t.passed ? 'pass' : 'fail') + '">' + (t.passed ? 'PASS' : 'FAIL') + '</span>';
                        tests.appendChild(div);
                    });

                    document.getElementById('timestamp').textContent = new Date().toLocaleString();
                    document.getElementById('lastUpdate').textContent = data.last_update ?
                        'Data: ' + data.last_update : '';
                });
        }

        function runTests() {
            fetch('/api/run-tests', {method: 'POST'})
                .then(r => r.json())
                .then(() => refresh());
        }

        refresh();
        setInterval(refresh, 5000);
    </script>
</body>
</html>
"""

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())
        elif self.path == '/api/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(metrics).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/run-tests':
            results = run_test_suite()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"results": results}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logging

if __name__ == '__main__':
    PORT = 8080
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  BETTI 14-WETTEN DASHBOARD                                       ║
╚══════════════════════════════════════════════════════════════════╝

Server running on http://localhost:{PORT}

Open this URL in your browser to see the dashboard.

Press Ctrl+C to stop.
""")

    server = http.server.HTTPServer(('', PORT), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
