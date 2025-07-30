import sys
from typing import Any

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers

def generate_local_accounts_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Gathers and reports detailed local user accounts and administrator status."""
    app_instance.log_output("\n--- Generating Detailed Local User Accounts Report ---")
    
    html_body = "<h2>Local User Accounts</h2>"

    if sys.platform == "win32":
        app_instance.log_output("Gathering Windows local accounts via WMIC...")
        wmic_output = helpers.run_command("wmic useraccount get Name,SID,Status,Disabled /format:list", app_instance=app_instance)
        users = []
        if wmic_output:
            user_blocks = wmic_output.strip().split('\n\n')
            for block in user_blocks:
                if not block.strip(): continue
                user_data = {}
                for line in block.strip().split('\n'):
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        user_data[parts[0].strip()] = parts[1].strip()
                if user_data:
                    users.append(user_data)

        admin_group_output = helpers.run_command("net localgroup Administrators", check_shell=True, app_instance=app_instance)
        admin_members = []
        if admin_group_output and "Members" in admin_group_output:
            try:
                lines = admin_group_output.split('-------------------------------------------------------------------------------')[1]
                admin_members = [name.strip() for name in lines.strip().split() if name.strip()]
            except IndexError:
                app_instance.log_output("Could not parse administrator list.")

        html_body += "<h3>All Local User Accounts</h3>"
        html_body += "<table><tr><th>Name</th><th>SID</th><th>Status</th><th>Disabled</th><th>Is Admin</th></tr>"
        for user in sorted(users, key=lambda x: x.get("Name", "")):
            name = user.get("Name", "N/A")
            is_admin = "Yes" if name in admin_members else "No"
            html_body += f"<tr><td>{name}</td><td>{user.get('SID', 'N/A')}</td><td>{user.get('Status', 'N/A')}</td><td>{user.get('Disabled', 'N/A')}</td><td>{is_admin}</td></tr>"
        html_body += "</table>"
    
    elif sys.platform.startswith("linux"):
        app_instance.log_output("Gathering Linux local accounts from /etc/passwd...")
        passwd_output = helpers.run_command("awk -F: '{print $1, $3, $6, $7}' /etc/passwd", check_shell=True, app_instance=app_instance)
        
        html_body += "<h3>Linux User Accounts (from /etc/passwd)</h3>"
        html_body += "<table><tr><th>Username</th><th>UID</th><th>Home Directory</th><th>Shell</th></tr>"
        if passwd_output:
            for line in passwd_output.strip().split('\n'):
                parts = line.strip().split()
                if len(parts) >= 1:
                    username = parts[0]
                    uid = parts[1] if len(parts) > 1 else "N/A"
                    home_dir = parts[2] if len(parts) > 2 else "N/A"
                    shell = parts[3] if len(parts) > 3 else "N/A"
                    html_body += f"<tr><td>{username}</td><td>{uid}</td><td>{home_dir}</td><td>{shell}</td></tr>"
        else:
            html_body += "<tr><td colspan='4'>Could not read /etc/passwd.</td></tr>"
        html_body += "</table>"

    elif sys.platform == "darwin":
        app_instance.log_output("Gathering macOS local accounts and details...")
        users_list_output = helpers.run_command("dscl . -list /Users", check_shell=True, app_instance=app_instance)
        standard_users, system_users = [], []

        if users_list_output:
            all_usernames = [u.strip() for u in users_list_output.strip().split('\n') if u.strip()]
            for username in all_usernames:
                details_output = helpers.run_command(f"dscl . -read /Users/{username} UniqueID NFSHomeDirectory UserShell RealName", check_shell=True, app_instance=app_instance)
                user_data = {'Name': username}
                if details_output:
                    for line in details_output.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            user_data[key.strip()] = value.strip()
                if username.startswith('_'):
                    system_users.append(user_data)
                else:
                    standard_users.append(user_data)
        
        admin_members_output = helpers.run_command("dscl . -read /Groups/admin GroupMembership", check_shell=True, app_instance=app_instance)
        admin_usernames = []
        if admin_members_output and "GroupMembership:" in admin_members_output:
            admin_usernames = admin_members_output.split("GroupMembership:")[1].strip().split()
        
        html_body += "<h3>Standard & Administrator Accounts</h3>"
        html_body += "<table><tr><th>Name</th><th>Real Name</th><th>Is Admin</th><th>UniqueID</th><th>Home Directory</th><th>Login Shell</th></tr>"
        for user in sorted(standard_users, key=lambda x: int(x.get('UniqueID', 9999))):
            name = user.get('Name', 'N/A')
            is_admin = "Yes" if name in admin_usernames else "No"
            html_body += f"<tr><td>{name}</td><td>{user.get('RealName', 'N/A')}</td><td>{is_admin}</td><td>{user.get('UniqueID', 'N/A')}</td><td>{user.get('NFSHomeDirectory', 'N/A')}</td><td>{user.get('UserShell', 'N/A')}</td></tr>"
        html_body += "</table>"

        html_body += "<h3>System Accounts</h3>"
        html_body += "<table><tr><th>Name</th><th>Real Name</th><th>UniqueID</th><th>Home Directory</th><th>Login Shell</th></tr>"
        for user in sorted(system_users, key=lambda x: x.get('Name')):
            html_body += f"<tr><td>{user.get('Name', 'N/A')}</td><td>{user.get('RealName', 'N/A')}</td><td>{user.get('UniqueID', 'N/A')}</td><td>{user.get('NFSHomeDirectory', 'N/A')}</td><td>{user.get('UserShell', 'N/A')}</td></tr>"
        html_body += "</table>"

    html_body += "<h3>Analyst Notes</h3>"
    html_body += "<p>To identify potentially compromised accounts, analysts should look for:</p>"
    html_body += "<ul>"
    html_body += "<li><b>Unexpected Administrators:</b> Accounts with admin privileges that are not documented or expected.</li>"
    html_body += "<li><b>Anomalous Shells:</b> Users with interactive login shells (e.g., /bin/bash) that shouldn't have them (like service accounts).</li>"
    html_body += "<li><b>Unusual Home Directories:</b> Home directories in unexpected locations like /tmp or /var/tmp.</li>"
    html_body += "<li><b>Low UIDs:</b> On Linux/macOS, a non-root user with a low UID (e.g., < 500) can be suspicious.</li>"
    html_body += "</ul>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Local_Accounts_Report.html", 
        "Local User Accounts Report", 
        html_body,
        browser_preference=browser_preference
    )