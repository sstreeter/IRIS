import sys
import os
from typing import Any

# Import necessary components from helpers.py
from helpers import MockAppInstance, MockHelpers

def generate_user_security_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Gathers and reports local user accounts and basic security indicators."""
    app_instance.log_output("\n--- Generating User & Security Report ---")
    
    html_body = ""

    # --- Local User Accounts ---
    html_body += "<h2>Local User Accounts</h2>"
    if sys.platform == "win32":
        app_instance.log_output("Gathering Windows local accounts and profiles...")
        local_users_output = helpers.run_command("net user", check_shell=True, app_instance=app_instance)
        admin_group_output = helpers.run_command("net localgroup Administrators", check_shell=True, app_instance=app_instance)
        
        html_body += "<h3>Local Users (basic output from 'net user'):</h3>"
        if local_users_output:
            html_body += f"<pre>{local_users_output}</pre>"
        html_body += "<h3>Local Administrators (basic output from 'net localgroup Administrators'):</h3>"
        if admin_group_output:
            html_body += f"<pre>{admin_group_output}</pre>"

    elif sys.platform == "darwin":
        app_instance.log_output("Gathering macOS local accounts and admin group membership...")
        
        users_list = helpers.run_command("dscl . -list /Users", check_shell=True, app_instance=app_instance)
        if users_list:
            html_body += "<table><tr><th>Username</th><th>Is Admin</th></tr>"
            admin_members_output = helpers.run_command("dscl . -read /Groups/admin GroupMembership", check_shell=True, app_instance=app_instance)
            admin_members = []
            if admin_members_output and "GroupMembership:" in admin_members_output:
                admin_members = admin_members_output.split("GroupMembership:")[1].strip().split()
            
            for user in users_list.strip().split('\n'):
                is_admin = "Yes" if user.strip() in admin_members else "No"
                html_body += f"<tr><td>{user.strip()}</td><td>{is_admin}</td></tr>"
            html_body += "</table>"
        
        html_body += "<h3>User Home Directories:</h3><table><tr><th>Path</th></tr>"
        home_dirs = helpers.run_command("ls /Users", check_shell=True, app_instance=app_instance)
        if home_dirs:
            for d in home_dirs.strip().split('\n'):
                html_body += f"<tr><td>/Users/{d.strip()}</td></tr>"
        html_body += "</table>"
    html_body += "<p>Note: Full user profile details require deeper forensic tools.</p>"

    # --- Logon Report (Placeholder) ---
    html_body += "<h2>Logon Report</h2>"
    html_body += "<p>Logon activity reporting is not yet implemented. This would typically involve parsing security event logs (Windows) or unified logs (macOS) for login/logout events.</p>"

    # --- Antivirus Status (Placeholder) ---
    html_body += "<h2>Antivirus Status</h2>"
    html_body += "<p>Antivirus status reporting is not yet implemented. This would require querying specific AV software APIs or well-known system locations.</p>"

    # --- Web History (Placeholder) ---
    html_body += "<h2>Web History</h2>"
    html_body += "<p>Web browsing history collection is not yet implemented. This would involve parsing browser-specific history databases (e.g., SQLite files for Chrome/Firefox).</p>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "User_Security_Report.html", 
        "User Accounts & Basic Security Report", 
        html_body,
        browser_preference=browser_preference
    )

