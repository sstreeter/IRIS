import sys
from typing import Any

# Import necessary components from helpers.py
from helpers import MockAppInstance, MockHelpers

def generate_network_connectivity_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Gathers and reports network connectivity details, including TCP connections."""
    app_instance.log_output("\n--- Generating Network Connectivity Report ---")
    
    html_body = ""

    # --- TCP Connections (Netstat) ---
    html_body += "<h2>Active Network Connections (Netstat)</h2><table><tr><th>Protocol</th><th>Local Address</th><th>Foreign Address</th><th>State</th></tr>"
    
    netstat_output = helpers.run_command("sudo netstat -an", check_shell=True, app_instance=app_instance)
    if netstat_output:
        for line in netstat_output.strip().split('\n'):
            if line.strip().startswith(('TCP', 'UDP', 'tcp', 'udp')):
                fields = line.strip().split()
                if len(fields) >= 4:
                    protocol = fields[0]
                    local_address = fields[1]
                    foreign_address = fields[2]
                    state = fields[3] if len(fields) > 3 else "N/A"
                    html_body += f"<tr><td>{protocol}</td><td>{local_address}</td><td>{foreign_address}</td><td>{state}</td></tr>"
        if not html_body.strip().endswith("</tr>"): # Check if any rows were added
            html_body += "<tr><td colspan='4'>No network connections found or permission denied. Try running with elevated privileges.</td></tr>"
    else:
        html_body += "<tr><td colspan='4'>Could not retrieve Netstat output. Try running with elevated privileges.</td></tr>"
    html_body += """</table>"""

    # --- Network Report (General Configuration - Placeholder) ---
    html_body += "<h2>General Network Configuration</h2>"
    if sys.platform == "darwin":
        html_body += "<h3>macOS Network Interfaces (ifconfig)</h3><pre>"
        ifconfig_output = helpers.run_command("ifconfig", check_shell=True, app_instance=app_instance)
        if ifconfig_output:
            html_body += ifconfig_output
        else:
            html_body += "Could not retrieve network interface information."
        html_body += "</pre>"

        html_body += "<h3>macOS DNS Configuration (scutil --dns)</h3><pre>"
        dns_output = helpers.run_command("scutil --dns", check_shell=True, app_instance=app_instance)
        if dns_output:
            html_body += dns_output
        else:
            html_body += "Could not retrieve DNS information."
        html_body += "</pre>"
    elif sys.platform == "win32":
        html_body += "<h3>Windows IP Configuration (ipconfig /all)</h3><pre>"
        ipconfig_output = helpers.run_command("ipconfig /all", check_shell=True, app_instance=app_instance)
        if ipconfig_output:
            html_body += ipconfig_output
        else:
            html_body += "Could not retrieve network configuration."
        html_body += "</pre>"
    else:
        html_body += "<p>Network configuration details for this OS are not yet fully implemented.</p>"


    # --- Firewall Rules (Placeholder) ---
    html_body += "<h2>Firewall Rules</h2>"
    html_body += "<p>Firewall rules reporting is not yet implemented. This would involve querying OS-specific firewall configurations (e.g., `pfctl` on macOS, `netsh advfirewall` on Windows).</p>"


    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Network_Connectivity_Report.html", 
        "Network Connectivity Report", 
        html_body,
        browser_preference=browser_preference
    )

