import sys
from typing import Any

from ...helpers import MockAppInstance, Helpers

def generate_network_config_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Gathers and reports detailed network configuration for the host OS."""
    app_instance.log_output("\n--- Generating Network Configuration Report ---")
    
    html_body = "<h2>Network Configuration</h2>"

    if sys.platform == "darwin":
        html_body += "<h3>Network Interfaces (ifconfig)</h3>"
        ifconfig_output = helpers.run_command("ifconfig -a", check_shell=True, app_instance=app_instance)
        if ifconfig_output:
            html_body += f"<pre>{ifconfig_output}</pre>"
        else:
            html_body += "<p>Could not retrieve network interface information.</p>"

        html_body += "<h3>DNS Configuration (scutil --dns)</h3>"
        dns_output = helpers.run_command("scutil --dns", check_shell=True, app_instance=app_instance)
        if dns_output:
            html_body += f"<pre>{dns_output}</pre>"
        else:
            html_body += "<p>Could not retrieve DNS information.</p>"

    elif sys.platform == "win32":
        html_body += "<h3>Network Configuration (ipconfig /all)</h3>"
        ipconfig_output = helpers.run_command("ipconfig /all", check_shell=True, app_instance=app_instance)
        if ipconfig_output:
            html_body += f"<pre>{ipconfig_output}</pre>"
        else:
            html_body += "<p>Could not retrieve network interface information.</p>"
            
    else:
        html_body += "<p>Network configuration reporting is not implemented for this OS.</p>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Network_Config_Report.html", 
        "Network Configuration Report", 
        html_body,
        browser_preference=browser_preference
    )