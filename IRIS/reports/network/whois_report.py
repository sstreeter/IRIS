import sys
from typing import Any
from ...helpers import Helpers, MockAppInstance

def generate_whois_report(app_instance: Any, helpers: Helpers, target: str = None, browser_preference: str = "System Default"):
    """
    Performs a WHOIS lookup for a given domain and generates a report.
    """
    app_instance.log_output("\n--- Generating WHOIS Report ---")
    
    if not target:
        target = helpers.ask_user_input(
            "Enter Domain to lookup:", 
            default_answer="google.com", 
            timeout=20, 
            app_instance=app_instance
        )
    
    if not target or target == "Cancelled":
        app_instance.log_output("WHOIS lookup cancelled by user or timed out.")
        return

    app_instance.log_output(f"Performing WHOIS lookup for {target}...")
    # whois command is native on macOS
    raw_out = helpers.run_command(f"whois {target}", check_shell=True, app_instance=app_instance)
    
    html_body = f"<h2>WHOIS Results for: {target}</h2>"
    
    if raw_out:
        html_body += f"<pre>{raw_out}</pre>"
    else:
        html_body += f"<p>No WHOIS data returned for {target}.</p>"
        
    # Add external investigation links
    html_body += "<h3>External Investigation</h3>"
    html_body += "<ul>"
    html_body += f"<li><a href='https://www.whois.com/whois/{target}' target='_blank'>View on Whois.com</a></li>"
    html_body += f"<li><a href='https://www.virustotal.com/gui/domain/{target}' target='_blank'>View on VirusTotal</a></li>"
    html_body += "</ul>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        f"Whois_Report_{target.replace('.', '_')}.html", 
        f"WHOIS Report - {target}", 
        html_body,
        browser_preference=browser_preference
    )
