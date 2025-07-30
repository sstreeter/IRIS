import sys
from typing import Any

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers

def generate_network_traffic_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """
    Captures a snapshot of network traffic using nethogs or tcpdump.
    Note: This requires running the main script with sudo on Linux.
    """
    app_instance.log_output("\n--- Generating Network Traffic Analysis Report ---")
    
    html_body = "<h2>Network Traffic Analysis (Snapshot)</h2>"
    html_body += "<p><strong>Disclaimer:</strong> This report provides a brief snapshot of network activity. For deep traffic inspection, continuous monitoring with tools like Suricata, Zeek, or Wireshark is recommended. Running these commands may require administrator (sudo) privileges.</p>"

    if sys.platform.startswith("linux"):
        app_instance.log_output("Attempting to capture traffic with nethogs...")
        # nethogs shows per-process bandwidth. -t for trace mode, -c for count.
        nethogs_output = helpers.run_command("sudo nethogs -t -c 5", check_shell=True, app_instance=app_instance)

        if nethogs_output and "nethogs: command not found" not in nethogs_output:
            html_body += "<h3>Nethogs Bandwidth Snapshot</h3>"
            html_body += "<p>The following shows the top network-consuming processes over a short period.</p>"
            html_body += f"<pre>{nethogs_output}</pre>"
        else:
            app_instance.log_output("Nethogs not found or failed. Falling back to tcpdump...")
            html_body += "<h3>TCPDump Packet Snapshot</h3>"
            html_body += "<p>Nethogs was not available. The following is a small sample of network packets captured with tcpdump.</p>"
            # tcpdump -c captures a specific count of packets. -n prevents DNS resolution.
            tcpdump_output = helpers.run_command("sudo tcpdump -c 20 -n", check_shell=True, app_instance=app_instance)
            if tcpdump_output:
                html_body += f"<pre>{tcpdump_output}</pre>"
            else:
                html_body += "<p>Could not capture traffic with tcpdump. Ensure it is installed and the script has sufficient permissions.</p>"

    else:
        html_body += "<p>Network traffic snapshot is currently implemented for Linux systems only.</p>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Network_Traffic_Report.html", 
        "Network Traffic Report", 
        html_body,
        browser_preference=browser_preference
    )