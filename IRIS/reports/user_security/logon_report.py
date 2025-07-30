import sys
from typing import Any

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers

def generate_logon_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Generates a report on logon activity and user creation events."""
    app_instance.log_output("\n--- Generating Logon Report ---")
    
    html_body = "<h2>Logon & User Creation Report</h2>"

    if sys.platform.startswith("linux"):
        app_instance.log_output("Searching for user creation and SSH login events in /var/log/auth.log...")
        # Grep for useradd events and successful/failed SSH logins
        logon_events = helpers.run_command(
            "grep -E 'useradd|sshd.*(Accepted|Failed)' /var/log/auth.log",
            check_shell=True,
            app_instance=app_instance
        )

        html_body += "<h3>Linux User Creation & SSH Login Events</h3>"
        if logon_events:
            html_body += "<p>The following are relevant raw events from <code>/var/log/auth.log</code>. Review for unauthorized user creation or suspicious login patterns.</p>"
            html_body += f"<pre>{logon_events}</pre>"
        else:
            html_body += "<p>No recent user creation or SSH login events found in <code>/var/log/auth.log</code>.</p>"

    else:
        html_body += "<p>Logon activity reporting for this OS is not yet fully implemented. This would typically involve parsing security event logs (Windows) or unified logs (macOS) for login/logout events.</p>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Logon_Report.html", 
        "Logon Report", 
        html_body,
        browser_preference=browser_preference
    )