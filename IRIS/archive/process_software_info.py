import sys
import json
from typing import Any

# Import necessary components from helpers.py
from helpers import MockAppInstance, MockHelpers

def generate_process_software_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Gathers and reports running processes and installed software."""
    app_instance.log_output("\n--- Generating Process & Software Report ---")
    
    html_body = ""

    # --- Running Processes ---
    html_body += "<h2>Running Processes</h2><table><tr><th>Name</th><th>PID</th><th>User</th></tr>"
    if sys.platform == "win32":
        processes_output = helpers.run_command(r"powershell.exe -Command \"Get-Process | Select-Object ProcessName, Id, @{Name='UserName';Expression={$_.Owner)}\"", app_instance=app_instance)
        if processes_output:
            for line in processes_output.strip().split('\n')[3:]:
                parts = line.strip().split(None, 2)
                if len(parts) == 3:
                    name = parts[0]
                    pid = parts[1]
                    user = parts[2]
                    html_body += f"<tr><td>{name}</td><td>{pid}</td><td>{user}</td></tr>"
        else:
            html_body += "<tr><td colspan='3'>Could not retrieve Windows processes.</td></tr>"
    elif sys.platform == "darwin":
        processes_output = helpers.run_command("ps aux", check_shell=True, app_instance=app_instance)
        if processes_output:
            for line in processes_output.strip().split('\n')[1:]:
                parts = line.strip().split(None, 10)
                if len(parts) >= 11:
                    user = parts[0]
                    pid = parts[1]
                    cmd = " ".join(parts[10:])
                    html_body += f"<tr><td>{cmd}</td><td>{pid}</td><td>{user}</td></tr>"
        else:
            html_body += "<tr><td colspan='3'>Could not retrieve macOS processes.</td></tr>"
    html_body += "</table>"

    # --- Installed Software (Placeholder) ---
    html_body += "<h2>Installed Software</h2>"
    if sys.platform == "win32":
        html_body += "<h3>Windows Installed Programs (via WMIC)</h3><pre>"
        software_output = helpers.run_command("wmic product get Name,Version /format:list", app_instance=app_instance)
        if software_output:
            html_body += software_output
        else:
            html_body += "Could not retrieve installed software information."
        html_body += "</pre>"
    elif sys.platform == "darwin":
        html_body += "<h3>macOS Installed Applications (Common Locations)</h3>"
        html_body += "<p>This is a basic listing of applications found in common directories. A comprehensive list would require parsing receipts or other package management data.</p>"
        html_body += "<h4>/Applications/</h4><pre>"
        app_list_output = helpers.run_command("ls -F /Applications/ | grep '/'", check_shell=True, app_instance=app_instance)
        if app_list_output:
            html_body += app_list_output
        else:
            html_body += "Could not list applications in /Applications/."
        html_body += "</pre>"
        html_body += "<h4>~/Applications/</h4><pre>"
        user_app_list_output = helpers.run_command("ls -F ~/Applications/ | grep '/'", check_shell=True, app_instance=app_instance)
        if user_app_list_output:
            html_body += user_app_list_output
        else:
            html_body += "Could not list applications in ~/Applications/."
        html_body += "</pre>"
    else:
        html_body += "<p>Installed software reporting for this OS is not yet fully implemented.</p>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Process_Software_Report.html", 
        "Running Processes & Installed Software Report", 
        html_body,
        browser_preference=browser_preference
    )

