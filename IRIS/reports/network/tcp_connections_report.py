import sys
from typing import Any

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers

def generate_tcp_connections_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """
    Gathers and reports active TCP/UDP connections and listening ports
    using the best available tool for the host OS.
    """
    app_instance.log_output("\n--- Generating TCP/UDP Connections Report ---")
    
    html_body = "<h2>Active Network Connections & Listening Ports</h2>"
    
    command_to_run = ""
    if sys.platform.startswith("linux"):
        # 'ss' is the modern replacement for 'netstat' on Linux
        # -t: tcp, -u: udp, -l: listening, -p: process, -n: numeric
        command_to_run = "ss -tulpn"
        html_body += f"<h3>Linux Connections (via '{command_to_run}')</h3>"

    elif sys.platform == "darwin":
        # 'lsof' is powerful on macOS for showing connections and processes
        # -i: list internet files, -P: numeric ports, -n: numeric hosts
        command_to_run = "lsof -i -P -n | grep -E 'LISTEN|ESTABLISHED'"
        html_body += f"<h3>macOS Connections (via 'lsof')</h3>"

    elif sys.platform == "win32":
        # 'netstat' is the standard on Windows
        # -a: all, -n: numeric, -o: show owning process ID
        command_to_run = "netstat -ano"
        html_body += f"<h3>Windows Connections (via '{command_to_run}')</h3>"

    if command_to_run:
        app_instance.log_output(f"Gathering network connections with: {command_to_run}")
        connections_output = helpers.run_command(command_to_run, check_shell=True, app_instance=app_instance)
        if connections_output:
            html_body += f"<pre>{connections_output}</pre>"
        else:
            html_body += "<p>Could not retrieve network connection information.</p>"
    else:
        html_body += "<p>Network connection reporting is not supported on this operating system.</p>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "TCP_Connections_Report.html", 
        "TCP-UDP Connections Report", 
        html_body,
        browser_preference=browser_preference
    )