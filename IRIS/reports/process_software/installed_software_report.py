import sys
from typing import Any # ADDED: Import typing hints

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers

def generate_installed_software_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Gathers and reports installed software."""
    app_instance.log_output("\n--- Generating Installed Software Report ---")
    
    html_body = "<h2>Installed Software</h2>"
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
        "Installed_Software_Report.html", 
        "Installed Software Report", 
        html_body,
        browser_preference=browser_preference
    )

