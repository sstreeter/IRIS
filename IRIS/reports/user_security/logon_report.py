import re
from typing import List, Dict, Any
from ...helpers import MockAppInstance, Helpers
from ...analysis.security_advisor import SecurityAdvisor

def get_logon_data(helpers: Helpers, app_instance: Any) -> Dict[str, Any]:
    """Collects logon information using system commands."""
    data = {
        "os_type": helpers.os_type,
        "logons": [],
        "summary": {"total": 0, "unique_users": 0}
    }
    
    app_instance.log_output("Gathering Logon History...")
    
    if helpers.os_type in ["darwin", "linux"]:
        # Use 'last' command
        # Output format examples:
        # spencer   ttys000                   Thu Jan  9 15:43   still logged in
        # reboot     system boot  6.0.0-kali3- Thu Jan  9 ...
        raw_output = helpers.run_command("last -n 50", check_shell=True, app_instance=app_instance)
        
        if raw_output:
            for line in raw_output.splitlines():
                if not line or line.startswith("wtmp begins") or line.strip() == "":
                    continue
                
                parts = line.split()
                if len(parts) > 2:
                    user = parts[0]
                    tty = parts[1]
                    # We store the raw line for display to preserve formatting of time/duration
                    data["logons"].append({
                        "user": user,
                        "tty": tty,
                        "raw": line
                    })

    # Basic stats
    data["summary"]["total"] = len(data["logons"])
    data["summary"]["unique_users"] = len(set(l["user"] for l in data["logons"]))
    
    return data

def generate_logon_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    app_instance.log_output("\n--- Generating Logon & User Creation Report ---")
    
    data = get_logon_data(helpers, app_instance)
    
    # Analyze
    advisor = SecurityAdvisor()
    # advisor.analyze_logons(data) 
    
    html_body = "<h2>Logon History (Last 50)</h2>"
    
    if data['logons']:
        html_body += f"<p>Total Events: {data['summary']['total']} | Unique Users: {data['summary']['unique_users']}</p>"
        html_body += "<table><thead><tr><th>User</th><th>TTY</th><th>Details</th></tr></thead><tbody>"
        for l in data['logons']:
            html_body += f"<tr><td>{l['user']}</td><td>{l['tty']}</td><td>{l['raw']}</td></tr>"
        html_body += "</tbody></table>"
    else:
        html_body += "<p>No logon history found (or command failed).</p>"

    helpers.generate_report_html(
        app_instance,
        app_instance.suspect_computer_name,
        "Logon_Report.html",
        "Logon & User Creation Report",
        html_body,
        browser_preference=browser_preference
    )