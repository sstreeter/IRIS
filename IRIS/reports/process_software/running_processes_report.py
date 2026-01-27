import sys
import re
from typing import Any, List, Dict

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers

def parse_ps_aux(output: str) -> List[Dict[str, str]]:
    """
    Parses `ps aux` output into a list of dictionaries.
    Handles variable whitespace and merging command arguments.
    """
    processes = []
    lines = output.splitlines()
    if not lines:
        return processes

    # Header: USER PID %CPU %MEM VSZ RSS TT STAT STARTED TIME COMMAND
    # Skipping header check for robustness, assuming standard format or checking first line
    start_idx = 1 if "USER" in lines[0] else 0
    
    for line in lines[start_idx:]:
        parts = line.split()
        if len(parts) < 11:
            continue
            
        # Standard ps aux columns
        p_user = parts[0]
        p_pid = parts[1]
        p_cpu = parts[2]
        p_mem = parts[3]
        # Skip VSZ/RSS/TT/STAT/STARTED/TIME for brevity in dict keys, or keep if needed
        # We really care about COMMAND (parts[10:] merged)
        p_command = " ".join(parts[10:])
        
        processes.append({
            "user": p_user,
            "pid": p_pid,
            "cpu": p_cpu,
            "mem": p_mem,
            "command": p_command
        })
        
    return processes

def classify_process(proc: Dict[str, str]) -> Dict[str, Any]:
    """
    Analyzes a process and assigns Severity, Category, and Description.
    """
    cmd = proc["command"]
    cmd_lower = cmd.lower()
    name = cmd.split()[0] # Binary name/path
    base_name = name.split("/")[-1]
    
    category = "Unknown"
    severity = "Info"
    description = ""
    
    # --- 1. Threats / Critical / Suspicious ---
    critical_keywords = ["nc", "netcat", "ncat", "socat", "meterpreter"]
    if any(k == base_name or f"/{k}" in name for k in critical_keywords):
        category = "Network Tool"
        severity = "Critical"
        description = "Potential reverse shell or data exfiltration tool."
        
    elif "curl" in base_name or "wget" in base_name:
        category = "Network Tool"
        severity = "Warning" # Common, but suspicious if user didn't run it
        description = "File download utility."

    # Interpeters
    interpreters = ["python", "python3", "perl", "ruby", "php", "sh", "bash", "zsh", "dash", "csh", "tcsh"]
    if any(k == base_name or f"/{k}" in name for k in interpreters):
        category = "Shell/Interpreter"
        if "python" in base_name:
             severity = "Warning"
             description = "Python script/interpreter."
        else:
             severity = "Info"
             description = "System shell."
             
        # Escalate if arguments look weird (simple heuristic)
        if "-c" in cmd or "base64" in cmd:
            severity = "High"
            description += " Running inline command or encoded payload."

    # --- 2. System Noise ---
    # Kernel & Core Services
    system_procs = [
        "kernel_task", "launchd", "syslogd", "cids_turbolicens", "dbfseventsd", "mds", "mds_stores",
        "logd", "distnoted", "notifyd", "disarbitrationd", "coreaudiod", "bluetoothd", "wifid",
        "spotlight", "fseventsd", "hidd", "windowserver", "loginwindow", "securityd", "configd",
        "powerd", "warmd", "usbmuxd", "locationd", "timed", "calendaragent", "icloud", "cloudd",
        "nsurlsessiond", "trustd", "syspolicyd", "analyticsd", "sandboxd", "tccd"
    ]
    
    if (base_name.lower() in system_procs or 
        base_name.startswith("com.apple.") or
        "/System/Library" in name or 
        "/usr/libexec" in name or 
        "/usr/sbin" in name): # Heuristic: system binaries
        category = "System"
        severity = "System" # Special internal tag for filtering
        description = "Background system process."

    # User Applications
    if "/Applications" in name and category == "Unknown":
        category = "User App"
        severity = "Safe"
        description = "User GUI Application."

    # --- 3. Refinement ---
    # Escalation: Sudo
    if "sudo " in cmd:
        severity = "High"
        description = "Process running with elevated privileges (sudo)."

    return {
        "category": category,
        "severity": severity,
        "description": description
    }


def generate_running_processes_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Gathers and reports running processes, classifying them into actionable events."""
    app_instance.log_output("\n--- Generating Running Processes Report ---")
    
    # 1. Gather Data
    raw_output = ""
    if sys.platform == "win32":
        # Powershell table format is hard to parse reliably without JSON, sticking to simplified text or mocking structured
        # For this refactor, let's assume macOS focus primarily as per user state, but handle win32 gracefully
         raw_output = helpers.run_command(r"powershell.exe -Command \"Get-Process | Select-Object ProcessName, Id, Path\"", app_instance=app_instance) # Simplified for now
         # Win32 parser would need to be different
         processes = [] 
    else:
        raw_output = helpers.run_command("ps aux", check_shell=True, app_instance=app_instance)
        processes = parse_ps_aux(raw_output)

    # 2. Classify
    events = [] # High/Critical/Warning/Info(Shells)
    user_apps = []
    system_noise = []
    
    for p in processes:
        classification = classify_process(p)
        p.update(classification)
        
        sev = p["severity"]
        
        if sev in ["Critical", "High", "Warning"]:
            events.append(p)
        elif sev == "System":
            system_noise.append(p)
        elif sev == "Safe" or p["category"] == "User App":
            user_apps.append(p)
        else:
            # Info / Unknown -> treat as event if specific category, else noise?
            # Shells go to events
            if "Shell" in p["category"]:
                events.append(p)
            else:
                # Default "Unknown" -> Events so user sees them
                events.append(p)

    # 3. Build HTML
    html_body = "<h2>Running Processes Analysis</h2>"
    
    html_body += """
    <style>
        .proc-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; table-layout: fixed; }
        .proc-table th, .proc-table td { padding: 8px; border: 1px solid #ddd; text-align: left; vertical-align: top; word-wrap: break-word; }
        .proc-table th { background-color: #f2f2f2; }
        .col-sev { width: 80px; }
        .col-pid { width: 60px; }
        .col-user { width: 80px; }
        .col-cmd { }
        
        .badge { padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; font-size: 0.8em; display: inline-block; text-align: center; width: 60px; }
        .badge-critical { background-color: #dc3545; }
        .badge-high { background-color: #fd7e14; }
        .badge-warning { background-color: #ffc107; color: black; }
        .badge-info { background-color: #17a2b8; }
        .badge-safe { background-color: #28a745; }
        .badge-system { background-color: #6c757d; }
    </style>
    """

    def build_table(procs, title, collapsed=False):
        if not procs: return ""
        
        section = ""
        if collapsed:
            section += f"<details><summary style='cursor:pointer; font-size: 1.2em; font-weight: bold; margin: 20px 0;'>{title} ({len(procs)}) <i>- Click to Expand</i></summary>"
        else:
            section += f"<h3>{title} ({len(procs)})</h3>"
            
        section += """
        <table class='proc-table'>
            <thead><tr>
                <th class='col-sev'>Severity</th>
                <th class='col-pid'>PID</th>
                <th class='col-user'>User</th>
                <th class='col-cmd'>Command / Process</th>
                <th>Details</th>
            </tr></thead>
            <tbody>
        """
        for p in procs:
            sev = p['severity'].lower()
            badge = f"<span class='badge badge-{sev}'>{p['severity'].upper()}</span>"
            cmd_display = p['command']
            if len(cmd_display) > 150: cmd_display = cmd_display[:147] + "..."
            
            section += f"<tr><td>{badge}</td><td>{p['pid']}</td><td>{p['user']}</td><td><code>{cmd_display}</code></td><td>{p['description']}</td></tr>"
            
        section += "</tbody></table>"
        if collapsed: section += "</details>"
        return section

    # Events Section
    if events:
        html_body += build_table(events, "Notable Events & Check Items")
    else:
        html_body += "<p>✅ No suspicious or notable process events detected.</p>"

    # User Apps
    html_body += build_table(user_apps, "User Applications")

    # System Noise
    html_body += build_table(system_noise, "Background System Processes (Noise)", collapsed=True)

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Running_Processes_Report.html", 
        "Running Processes Report", 
        html_body,
        browser_preference=browser_preference
    )