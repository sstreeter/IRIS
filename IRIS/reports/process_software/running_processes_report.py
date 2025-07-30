import sys
from typing import Any

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers

def generate_running_processes_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Gathers and reports running processes, with a special focus on Python processes."""
    app_instance.log_output("\n--- Generating Running Processes Report ---")
    
    html_body = "<h2>Running Processes</h2>"
    
    # --- Section 1: Full Process List ---
    html_body += "<h3>Full Process List</h3>"
    if sys.platform == "win32":
        processes_output = helpers.run_command(r"powershell.exe -Command \"Get-Process | Format-Table -AutoSize\"", app_instance=app_instance)
        if processes_output:
            html_body += f"<pre>{processes_output}</pre>"
        else:
            html_body += "<p>Could not retrieve Windows processes.</p>"
    
    elif sys.platform.startswith("linux") or sys.platform == "darwin":
        processes_output = helpers.run_command("ps aux", check_shell=True, app_instance=app_instance)
        if processes_output:
            html_body += f"<pre>{processes_output}</pre>"
        else:
            html_body += "<p>Could not retrieve system processes.</p>"

    # --- Section 2: Python Process Analysis ---
    html_body += "<h3>Python Process Analysis</h3>"
    html_body += "<p>The following processes were launched using a Python interpreter. Review these for unauthorized or suspicious scripts, as Python is a common tool for backdoors and utilities.</p>"
    
    found_python = False
    if sys.platform == "win32":
        python_procs = helpers.run_command(r"powershell.exe -Command \"Get-Process | Where-Object { $_.ProcessName -like '*python*' } | Select-Object ProcessName, Id, Path\"", app_instance=app_instance)
        if python_procs and "Get-Process" not in python_procs:
            html_body += f"<pre>{python_procs}</pre>"
            found_python = True

    elif sys.platform.startswith("linux") or sys.platform == "darwin":
        # The '[]' trick in grep prevents the grep process itself from appearing in the output
        python_procs = helpers.run_command("ps aux | grep '[p]ython'", check_shell=True, app_instance=app_instance)
        if python_procs:
            html_body += f"<pre>{python_procs}</pre>"
            found_python = True
            
    if not found_python:
        html_body += "<p>No active processes running under a Python interpreter were found.</p>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Running_Processes_Report.html", 
        "Running Processes Report", 
        html_body,
        browser_preference=browser_preference
    )