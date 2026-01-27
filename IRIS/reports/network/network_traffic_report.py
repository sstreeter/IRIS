import sys
from typing import Any

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers

def generate_network_traffic_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """
    Captures a snapshot of network traffic using nethogs or tcpdump.
    Uses new structured tables and sudo upgrades.
    """
    app_instance.log_output("\n--- Generating Network Traffic Analysis Report ---")
    
    html_body = "<h2>Network Traffic Analysis (Snapshot)</h2>"
    
    html_body += """
    <style>
        .net-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.9em; table-layout: fixed; }
        .net-table th, .net-table td { padding: 6px; border: 1px solid #ddd; text-align: left; vertical-align: top; word-wrap: break-word; }
        .net-table th { background-color: #f2f2f2; }
    </style>
    """

    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        app_instance.log_output("Attempting to capture traffic details...")
        
        # 1. Try Nethogs (best for per-process visibility)
        # Note: Nethogs might not be installed or standard on macOS.
        # We'll use the new run_sudo_command 
        
        captured_data = False
        
        # On macOS, let's try 'nettop' as it's built-in, or just fall back to tcpdump 
        # But per requirements we will try to use the tools available.
        # If user has nethogs installed (via brew), great.
        
        nethogs_output = helpers.run_sudo_command("nethogs -t -c 5", prompt_text="IRIS needs permission to run nethogs for network traffic analysis.", app_instance=app_instance)
        
        if nethogs_output and "command not found" not in nethogs_output:
            html_body += "<h3>Process Network Usage (Nethogs)</h3>"
            html_body += "<table class='net-table'><tr><th>PID</th><th>Process/User</th><th>Sent</th><th>Received</th></tr>"
            
            lines = nethogs_output.strip().splitlines()
            count = 0
            for line in lines:
                # Nethogs trace mode output: "Process/Path/PID/User  KB/sec   KB/sec" (format varies)
                # It's unstructured text unfortunately in trace mode usually.
                # Let's simple-table it or put in pre if too hard to parse
                # For this improvement, let's just clean it up a bit or use parsed if possible.
                # Assuming raw dumping into table row for now to be better than <pre>
                parts = line.split()
                if len(parts) >= 3:
                     # Join first parts as process
                     proc = " ".join(parts[:-2])
                     sent = parts[-2]
                     recv = parts[-1]
                     html_body += f"<tr><td>?</td><td>{proc}</td><td>{sent} KB/s</td><td>{recv} KB/s</td></tr>"
                     count += 1
            html_body += "</table>"
            if count == 0: html_body += "<p>No traffic captured with nethogs.</p>"
            captured_data = True
            
        else:
            # Fallback to TCPDump
            app_instance.log_output("Nethogs not found or failed. Falling back to tcpdump...")
            html_body += "<h3>Packet Capture Snapshot (TCPDump)</h3>"
            html_body += "<p>Showing last 50 packets captured.</p>"
            
            # -nn: don't convert protocol/port numbers etc
            # -t: simpler timestamp
            tcpdump_output = helpers.run_sudo_command("tcpdump -c 50 -nn -t", prompt_text="IRIS needs permission to run tcpdump for network packet capture.", app_instance=app_instance)
            
            if tcpdump_output:
                 html_body += "<table class='net-table'><tr><th>Protocol</th><th>Source</th><th>Destination</th><th>Info/Flags</th></tr>"
                 for line in tcpdump_output.splitlines():
                     # Format: IP 1.2.3.4.123 > 5.6.7.8.80: Flags [S], seq ...
                     # Or: IP6 ...
                     parts = line.split()
                     if len(parts) > 4:
                         proto = parts[0] # IP/IP6 usually
                         try:
                             # Find the arrow ">"
                             arrow_idx = parts.index('>')
                             src = " ".join(parts[1:arrow_idx])
                             dst = parts[arrow_idx+1]
                             if dst.endswith(':'): dst = dst[:-1]
                             
                             info = " ".join(parts[arrow_idx+2:])
                             html_body += f"<tr><td>{proto}</td><td>{src}</td><td>{dst}</td><td>{info}</td></tr>"
                         except ValueError:
                             # formatting failed
                             html_body += f"<tr><td colspan='4'>{line}</td></tr>"
                     else:
                         html_body += f"<tr><td colspan='4'>{line}</td></tr>"
                 html_body += "</table>"
                 captured_data = True
            else:
                 html_body += "<p class='error'>Could not capture traffic. Sudo authentication may have failed or tools are missing.</p>"

    else:
        html_body += "<p>Network traffic snapshot is currently implemented for macOS/Linux systems only.</p>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Network_Traffic_Report.html", 
        "Network Traffic Report", 
        html_body,
        browser_preference=browser_preference
    )