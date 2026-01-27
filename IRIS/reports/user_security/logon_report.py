import re
from typing import List, Dict, Any
from collections import defaultdict
from ...helpers import MockAppInstance, Helpers

def parse_last_output(output: str) -> List[Dict[str, Any]]:
    """Parses `last` command output into structured data."""
    events = []
    # Lines look like:
    # spencer   ttys000                   Thu Jan  9 15:43   still logged in
    # root      pts/0        192.168.1.5  Wed Jan  8 10:00 - 10:20  (00:20)
    # reboot    system boot  ...
    
    for line in output.splitlines():
        if not line or line.startswith("wtmp begins") or line.strip() == "":
            continue
        
        parts = line.split()
        if len(parts) < 3: continue
        
        user = parts[0]
        tty = parts[1]
        
        # Heuristic for remote host (if 3rd part looks like IP or host, usually it's remote)
        # Standard `last` on macOS: User TTY Host(optional) Day Month Date Time ...
        # If Host is missing, the Day is the 3rd column?
        # check if parts[2] is a day of week (Mon,Tue...)
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        host = "Local"
        
        # Simple heuristic: if parts[2] is not a day, it's likely a host
        if parts[2] not in days:
            host = parts[2]
            # Time payload likely starts at parts[3]
            timestamp_parts = parts[3:]
        else:
            timestamp_parts = parts[2:]
            
        timestamp_str = " ".join(timestamp_parts)
        
        # Classify Type
        login_type = "Unknown"
        if "console" in tty:
            login_type = "GUI (Physical)"
        elif "ttys" in tty:
            login_type = "Terminal (Local/SSH)" # macOS often uses ttys for Terminal.app
        elif "pts" in tty:
            login_type = "Remote (SSH/Pts)"
        elif "boot" in user or "shutdown" in user:
            login_type = "System Event"
            
        events.append({
            "user": user,
            "tty": tty,
            "host": host,
            "time_str": timestamp_str,
            "type": login_type,
            "raw": line
        })
        
    return events

def analyze_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Groups events by user and flags suspicious ones."""
    grouped = defaultdict(list)
    suspicious = []
    
    for e in events:
        grouped[e["user"]].append(e)
        
        # Analysis
        flags = []
        if e["user"] == "root" and e["type"] != "System Event":
             flags.append("Root Login")
        
        if e["host"] != "Local" and e["type"] != "System Event":
             # External IP check? For now just flag remote
             if "Remote" in e["type"] or "pts" in e["tty"]:
                 flags.append("Remote Login")
                 
        if flags:
            e["flags"] = flags
            # e["severity"] = "High" if "Root Login" in flags else "Warning"
            
    return grouped

def generate_logon_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    app_instance.log_output("\n--- Generating Logon & User Creation Report ---")
    
    # Dynamic Input: Ask for number of events
    default_count = "50"
    prompt = "Number of logon events to analyze?"
    
    if helpers.os_type in ["darwin", "linux"]:
        # Get total available count estimate
        try:
             # Count lines in output, ignoring empty lines
             count_out = helpers.run_command("last | grep -v '^$' | wc -l", check_shell=True, app_instance=app_instance)
             if count_out and count_out.strip().isdigit():
                 total = int(count_out.strip())
                 # 'last' output usually has a trailing "wtmp begins..." line, so maybe subtract 1?
                 # Approximation is fine for UX.
                 prompt = f"Number of logon events to analyze? (Max available: ~{total})"
        except Exception:
            pass # Fallback to generic prompt if check fails
            
    count_str = helpers.ask_user_input(prompt, default_count, 10, app_instance)
    
    try:
        count = int(count_str)
        if count <= 0: count = 50
    except ValueError:
        count = 50
        app_instance.log_output(f"Invalid input '{count_str}', defaulting to {count} events.")

    html_body = f"<h2>Logon History Analysis (Last {count} Events)</h2>"
    
    html_body += """
    <style>
        .user-group { background: #fff; border: 1px solid #ddd; margin-bottom: 10px; border-radius: 4px; }
        .user-summary { padding: 10px; cursor: pointer; background: #f9f9f9; font-weight: bold; list-style: none; display: flex; justify-content: space-between; align-items: center; }
        .user-summary::-webkit-details-marker { display: none; }
        .user-summary:hover { background: #eee; }
        .log-table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
        .log-table th, .log-table td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; }
        .badge { padding: 2px 6px; border-radius: 4px; font-size: 0.8em; color: white; display: inline-block; margin-right: 4px; }
        .bg-red { background-color: #dc3545; }
        .bg-orange { background-color: #fd7e14; }
        .bg-blue { background-color: #007bff; }
        .bg-gray { background-color: #6c757d; }
    </style>
    """
    
    if helpers.os_type in ["darwin", "linux"]:
        # Use 'last' command
        raw_output = helpers.run_command(f"last -n {count}", check_shell=True, app_instance=app_instance)
        
        if raw_output:
            events = parse_last_output(raw_output)
            grouped = analyze_events(events)
            
            # Summary Stats
            total_events = len(events)
            unique_users = len(grouped.keys())
            html_body += f"<p><strong>Total Events:</strong> {total_events} | <strong>Unique Accounts:</strong> {unique_users}</p>"
            
            # Render User Groups
            for user, user_events in sorted(grouped.items()):
                # Determine user severity/badges
                user_badges = ""
                if user in ["root"]: 
                    user_badges += "<span class='badge bg-red'>ROOT</span>"
                if any("Remote Login" in e.get("flags", []) for e in user_events):
                    user_badges += "<span class='badge bg-orange'>REMOTE ACCESS</span>"
                
                count = len(user_events)
                html_body += f"""
                <details class='user-group' {'open' if count < 5 else ''}>
                    <summary class='user-summary'>
                        <span>👤 {user} {user_badges}</span>
                        <span>{count} Events ▼</span>
                    </summary>
                    <div style='padding: 10px;'>
                        <table class='log-table'>
                            <thead><tr><th>Type</th><th>Source (Host)</th><th>Time/Duration</th><th>Flags</th></tr></thead>
                            <tbody>
                """
                
                for e in user_events:
                    # Row styling
                    type_badge = "bg-gray"
                    if "GUI" in e['type']: type_badge = "bg-blue"
                    elif "Remote" in e['type']: type_badge = "bg-orange"
                    
                    flags_html = ""
                    if e.get("flags"):
                        for f in e['flags']:
                            color = "bg-orange" if f == "Remote Login" else "bg-red"
                            flags_html += f"<span class='badge {color}'>{f}</span>"
                            
                    html_body += f"<tr><td><span class='badge {type_badge}'>{e['type']}</span> <small>({e['tty']})</small></td><td>{e['host']}</td><td>{e['time_str']}</td><td>{flags_html}</td></tr>"
                    
                html_body += """
                            </tbody>
                        </table>
                    </div>
                </details>
                """
        else:
             html_body += "<p>No output from `last` command.</p>"
    else:
        html_body += "<p>Logon history analysis is primarily for macOS/Linux in this module.</p>"

    helpers.generate_report_html(
        app_instance,
        app_instance.suspect_computer_name,
        "Logon_Report.html",
        "Logon & User Creation Report",
        html_body,
        browser_preference=browser_preference
    )