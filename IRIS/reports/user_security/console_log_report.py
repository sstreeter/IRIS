import sys
import re
import os
import json
from datetime import datetime, timedelta
from typing import Any, List, Dict, Optional
from ...helpers import MockAppInstance, Helpers

# --- Constants & Configuration ---
DIAG_DIRS = [
    "/Library/Logs/DiagnosticReports",
    os.path.expanduser("~/Library/Logs/DiagnosticReports"),
    "/var/log/DiagnosticMessages"
]

HUMAN_LABELS = {
    "authd": "Authentication Service",
    "securityd": "Security Framework",
    "opendirectoryd": "Directory Services",
    "sudo": "Sudo Privilege Elevation",
    "kernel": "macOS Kernel",
    "loginwindow": "Login Window",
    "configd": "System Configuration",
    "diskarbitrationd": "Disk Arbitration",
    "coreservicesd": "Core Services",
    "UserEventAgent": "User Event Agent",
    "tccd": "Transparency, Consent, and Control",
    "lsd": "Launch Services",
    "distnoted": "Distributed Notifications"
}

# Forensic Patterns for "Actionable Insights"
FORENSIC_INSIGHTS = {
    r"Authentication failed": ("Security", "Potential unauthorized access attempt detected."),
    r"failed to authenticate": ("Security", "Authentication failure. Verify credentials."),
    r"permission denied": ("Security", "Access restricted. Possible SIP or permission violation."),
    r"GPU Reset": ("Hardware", "Graphics hardware/driver instability detected."),
    r"I/O error": ("Hardware", "Critical disk I/O error. Hardware failure imminent?"),
    r"sudo: .* ; TTY": ("Security", "Administrative command executed via sudo."),
    r"Invalid password": ("Security", "Incorrect password entry."),
    r"EXC_BAD_ACCESS": ("Crash", "Memory corruption or invalid memory access detected."),
    r"EXC_CRASH": ("Crash", "Process terminated abnormally."),
    r"SIGABRT": ("Crash", "Process aborted itself (Assertion failure?)."),
    r"SIGSEGV": ("Crash", "Segmentation fault. Possible exploit attempt or bug."),
    r"Sandbox: .* deny": ("Security", "Sandbox violation. Process attempted restricted action."),
    r"malicious": ("Threat", "Indicator of malicious activity detected by XProtect/MRT."),
    r"killed": ("Process", "Process was terminated by the system (OOM or Signal).")
}

def get_human_label(process: str) -> str:
    return HUMAN_LABELS.get(process, process)

def get_forensic_insight(message: str) -> Optional[tuple]:
    for pattern, (category, insight) in FORENSIC_INSIGHTS.items():
        if re.search(pattern, message, re.I):
            return category, insight
    return None

def parse_crash_file(path: str) -> Dict[str, Any]:
    """Parses basic info from a .crash or .ips file."""
    info = {
        "Process": "Unknown",
        "Identifier": "Unknown",
        "Version": "Unknown",
        "Code Type": "Unknown",
        "Exception Type": "Unknown",
        "Date": "Unknown",
        "Path": path
    }
    try:
        with open(path, 'r', errors='ignore') as f:
            content = f.read(5000) # Only read start of file for metadata
            # Pattern matching for common crash header fields
            matches = {
                "Process": r"Process:\s+(.*)",
                "Identifier": r"Identifier:\s+(.*)",
                "Version": r"Version:\s+(.*)",
                "Code Type": r"Code Type:\s+(.*)",
                "Exception Type": r"Exception Type:\s+(.*)",
                "Date": r"Date/Time:\s+(.*)"
            }
            for key, pattern in matches.items():
                m = re.search(pattern, content)
                if m:
                    info[key] = m.group(1).split('[')[0].strip() # Clean [PID] etc
    except: pass
    return info

def generate_console_log_report(app_instance: Any, helpers: Helpers, browser_preference: str = "System Default"):
    """Gathers and reports security-relevant logs from the macOS Unified Logging System."""
    app_instance.log_output("\n--- Generating Forensic macOS Console Report ---")
    
    summary = {
        "Crashes": 0,
        "Spins": 0,
        "SecurityEvents": 0,
        "KernelFaults": 0,
        "Diagnostics": 0
    }

    # 1. GATHER DATA: Crash & Spin & Diag Reports
    app_instance.log_output("Parsing diagnostic and crash reports...")
    crash_reports = []
    spin_reports = []
    diag_reports = []
    
    for d_dir in DIAG_DIRS[:2]: # Only scan Library dirs for files
        if os.path.exists(d_dir):
            try:
                for f in os.listdir(d_dir):
                    path = os.path.join(d_dir, f)
                    if os.path.isdir(path): continue
                    
                    mtime = os.path.getmtime(path)
                    if datetime.now() - datetime.fromtimestamp(mtime) > timedelta(days=7):
                        continue
                        
                    ext = f.lower()
                    if ext.endswith(('.crash', '.ips')):
                        info = parse_crash_file(path)
                        info['FileName'] = f
                        crash_reports.append(info)
                        summary["Crashes"] += 1
                    elif ext.endswith(('.spin', '.hang')):
                        spin_reports.append({"file": f, "path": path, "date": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")})
                        summary["Spins"] += 1
                    elif ext.endswith('.diag'):
                        diag_reports.append({"file": f, "path": path, "date": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")})
                        summary["Diagnostics"] += 1
            except: pass

    # 2. GATHER DATA: Unified Logs (Log Reports)
    app_instance.log_output("Capturing Unified Log forensic stream (JSON)...")
    
    # Determine Time Range
    tr = getattr(app_instance, 'time_range', {"start": None, "end": None})
    start_time = tr.get('start')
    end_time = tr.get('end')
    
    base_cmd = "log show --style json"
    
    if start_time:
        # log show format: YYYY-MM-DD HH:MM:SS
        s_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        base_cmd += f" --start '{s_str}'"
        if end_time:
            e_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
            base_cmd += f" --end '{e_str}'"
    else:
        # Default to last 1h if no range is selected (or "All Time" but for logs All Time is huge, so we default to 1h unless customized)
        # Actually, if user says "All Time" for logs, that could be GBs. Let's default to 4h if explicit All Time, or Keep 1h default.
        # Ideally we respect "All Time" but warn? 
        # For now, let's say "All Time" = Last 24h for logs to prevent freeze.
        base_cmd += " --last 1h"

    # Forensic Predicates
    predicates = {
        "Security": '"(logType == 16 or logType == 17) and (process == \\"authd\\" or process == \\"securityd\\" or process == \\"opendirectoryd\\" or eventMessage contains \\"sudo\\" or subsystem contains \\"com.apple.security\\")"',
        "Kernel": '"logType == 16 and process == \\"kernel\\""',
        "Persistence": '"subsystem contains \\"com.apple.launchd\\" or eventMessage contains \\"Library/Launch\\""'
    }
    
    log_data = {}
    for cat, pred in predicates.items():
        out = helpers.run_sudo_command(f'{base_cmd} --predicate {pred}', app_instance=app_instance)
        try:
            items = json.loads(out) if out and out.strip() else []
            log_data[cat] = items
            if cat == "Security": summary["SecurityEvents"] += len(items)
            if cat == "Kernel": summary["KernelFaults"] += len(items)
        except:
            log_data[cat] = []

    # 3. GATHER DATA: Mac Analytics
    app_instance.log_output("Reading Mac Analytics Data...")
    analytics_data = []
    analytics_path = "/var/log/DiagnosticMessages"
    if os.path.exists(analytics_path):
        # We'll just list the recent message types from the filesystem as a proxy for analytics trends
        try:
            msg_files = os.listdir(analytics_path)
            for f in msg_files[:20]: # Cap it
                if f.endswith('.asl') or f.endswith('.log'):
                    analytics_data.append({"type": f.split('.')[0], "file": f})
        except: pass

    # 4. GATHER DATA: system.log
    app_instance.log_output("Tailing system.log...")
    sys_log = helpers.run_sudo_command("tail -n 100 /var/log/system.log", app_instance=app_instance)

    # --- HTML Building ---
    html_body = f"""
    <div class='forensic-header'>
        <h2>macOS Professional Forensic Console Report</h2>
        <p>Comprehensive analysis of system logs, crashes, and diagnostic telemetry.</p>
    </div>

    <!-- Section 0: Forensic Summary Dashboard -->
    <div class='dashboard'>
        <div class='stat-card' style='border-top: 4px solid #dc3545;'>
            <div class='stat-value'>{summary["Crashes"]}</div>
            <div class='stat-label'>Critical Crashes (7d)</div>
        </div>
        <div class='stat-card' style='border-top: 4px solid #ffc107;'>
            <div class='stat-value'>{summary["SecurityEvents"]}</div>
            <div class='stat-label'>Security Events (1h)</div>
        </div>
        <div class='stat-card' style='border-top: 4px solid #007bff;'>
            <div class='stat-value'>{summary["KernelFaults"]}</div>
            <div class='stat-label'>Kernel Faults (1h)</div>
        </div>
        <div class='stat-card' style='border-top: 4px solid #28a745;'>
            <div class='stat-value'>{summary["Diagnostics"] + summary["Spins"]}</div>
            <div class='stat-label'>Health Alerts (7d)</div>
        </div>
    </div>
    """

    # Section 1: Crash Reports
    html_body += "<div class='category-section' style='border-left: 5px solid #dc3545;'>"
    html_body += "<h3><i class='icon'>🔥</i> 1. Crash Reports</h3>"
    if crash_reports:
        html_body += "<table><thead><tr><th>Date</th><th>Process</th><th>Exception Type</th><th>Details</th></tr></thead><tbody>"
        for c in sorted(crash_reports, key=lambda x: x['Date'], reverse=True)[:20]:
            html_body += f"<tr><td>{c['Date']}</td><td><strong>{c['Process']}</strong></td><td><span class='badge bg-warn'>{c['Exception Type']}</span></td><td><small>{c['Identifier']}<br/>{c['FileName']}</small></td></tr>"
        html_body += "</tbody></table>"
    else: html_body += "<p class='no-data'>No crash reports found in the last 7 days.</p>"
    html_body += "</div>"

    # Section 2: Spin Reports
    html_body += "<div class='category-section' style='border-left: 5px solid #6f42c1;'>"
    html_body += "<h3><i class='icon'>⏳</i> 2. Spin & Hang Reports</h3>"
    if spin_reports:
        html_body += "<table><thead><tr><th>Date</th><th>Report File</th><th>Location</th></tr></thead><tbody>"
        for s in spin_reports[:10]:
            html_body += f"<tr><td>{s['date']}</td><td>{s['file']}</td><td><small>{s['path']}</small></td></tr>"
        html_body += "</tbody></table>"
    else: html_body += "<p class='no-data'>No application hangs or spin reports detected.</p>"
    html_body += "</div>"

    # Section 3: Log Reports (Unified Logs)
    html_body += "<div class='category-section' style='border-left: 5px solid #007bff;'>"
    html_body += "<h3><i class='icon'>📜</i> 3. Log Reports (Forensic Stream)</h3>"
    
    for subcat, items in log_data.items():
        if items:
            html_body += f"<h4>Category: {subcat}</h4>"
            html_body += "<table><thead><tr><th style='width:20%;'>Timestamp</th><th style='width:20%;'>Process</th><th>Message / Insight</th></tr></thead><tbody>"
            for log in items[:50]:
                msg = log.get("eventMessage", "")
                proc = log.get("process", "Unknown")
                ts = log.get("timestamp", "N/A")
                
                insight = get_forensic_insight(msg)
                insight_html = ""
                if insight:
                    insight_html = f"<div class='insight-pill'><span class='badge bg-info'>{insight[0]}</span> {insight[1]}</div>"
                
                html_body += f"<tr><td><small>{ts}</small></td><td><strong>{get_human_label(proc)}</strong></td><td>{msg}{insight_html}</td></tr>"
            html_body += "</tbody></table>"
        else:
            html_body += f"<p class='no-data'>No forensic {subcat} events in the last hour.</p>"
    html_body += "</div>"

    # Section 4: Diagnostic Reports
    html_body += "<div class='category-section' style='border-left: 5px solid #28a745;'>"
    html_body += "<h3><i class='icon'>🛠️</i> 4. Diagnostic Reports</h3>"
    if diag_reports:
        html_body += "<table><thead><tr><th>Date</th><th>Report Type</th><th>File</th></tr></thead><tbody>"
        for d in diag_reports[:15]:
            html_body += f"<tr><td>{d['date']}</td><td>System Diagnostic</td><td>{d['file']}</td></tr>"
        html_body += "</tbody></table>"
    else: html_body += "<p class='no-data'>No system diagnostics found.</p>"
    html_body += "</div>"

    # Section 5: Mac Analytics Data
    html_body += "<div class='category-section' style='border-left: 5px solid #17a2b8;'>"
    html_body += "<h3><i class='icon'>📊</i> 5. Mac Analytics Data Highlights</h3>"
    if analytics_data:
        html_body += "<div class='analytics-grid'>"
        for a in analytics_data:
            html_body += f"<div class='analytics-item'><strong>{a['type']}</strong><br/><small>{a['file']}</small></div>"
        html_body += "</div>"
    else: html_body += "<p class='no-data'>No analytics data available for display.</p>"
    html_body += "</div>"

    # Section 6: system.log
    html_body += "<div class='category-section' style='border-left: 5px solid #6c757d;'>"
    html_body += "<h3><i class='icon'>🖥️</i> 6. Traditional System Log (system.log)</h3>"
    if sys_log:
        html_body += f"<pre class='log-block'>{sys_log}</pre>"
    else: html_body += "<p class='no-data'>Could not retrieve system.log.</p>"
    html_body += "</div>"

    # Premium CSS Styling
    html_body += """
    <style>
        .forensic-header { background: linear-gradient(135deg, #1a1a1a 0%, #333 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 25px; }
        .forensic-header h2 { margin: 0; font-size: 1.8em; }
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); text-align: center; }
        .stat-value { font-size: 2em; font-weight: bold; color: #333; }
        .stat-label { font-size: 0.9em; color: #666; text-transform: uppercase; margin-top: 5px; }
        .category-section { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); }
        .category-section h3 { margin-top: 0; color: #333; font-size: 1.3em; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        .icon { font-style: normal; margin-right: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9em; }
        th, td { border: 1px solid #eee; padding: 10px; text-align: left; vertical-align: top; }
        th { background-color: #fcfcfc; color: #555; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; color: white; font-weight: bold; font-size: 0.75em; }
        .bg-warn { background-color: #dc3545; }
        .bg-info { background-color: #17a2b8; }
        .bg-sec { background-color: #6c757d; }
        .insight-pill { background: #f0fff4; border: 1px solid #c6f6d5; padding: 5px 10px; border-radius: 6px; margin-top: 8px; font-size: 0.85em; }
        .log-block { background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 8px; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.8em; max-height: 400px; overflow: auto; line-height: 1.4; }
        .analytics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
        .analytics-item { background: #f8f9fa; padding: 10px; border-radius: 6px; border: 1px solid #eee; font-size: 0.8em; }
        .no-data { color: #999; font-style: italic; }
        h4 { color: #0056b3; margin-bottom: 5px; margin-top: 20px; }
    </style>
    """

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Forensic_Console_Report.html", 
        "macOS Forensic Console Report", 
        html_body,
        browser_preference=browser_preference
    )
