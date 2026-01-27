import os
from pathlib import Path

# Define the root directory where IRISX_app will be created
# Set this to your desired location, e.g., "/Users/spencer/Projects/python/"
PROJECT_ROOT = "/Users/spencer/Projects/python/" 
APP_DIR_NAME = "IRISX_app"

app_path = Path(PROJECT_ROOT) / APP_DIR_NAME
utils_path = app_path / "utils"
modules_path = app_path / "modules"

# --- Content for each file ---

helpers_content = """
import subprocess
import os
import sys
import webbrowser # For opening reports
import datetime # For timestamps in reports
import tkinter as tk # Needed for app_instance type hinting / fallback output


def log_output(app_instance, message):
    \"\"\"Logs a message to the Tkinter output box.\"\"\"
    if app_instance:
        app_instance.output_box.insert(tk.END, message + "\\n")
        app_instance.output_box.see(tk.END) # Scroll to end
    else:
        print(message) # Fallback if app_instance is not provided (e.g., for direct module testing)

def run_command(command, check_shell=False, app_instance=None):
    \"\"\"
    Helper to run shell commands and capture output.
    Can log errors to the app_instance's output_box if provided.
    \"\"\"
    try:
        if sys.platform == "win32" and check_shell:
            # On Windows, some commands might need powershell.exe or cmd.exe explicitly
            process = subprocess.run(["powershell.exe", "-Command", command], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
        else:
            process = subprocess.run(command, capture_output=True, text=True, check=True, shell=check_shell)
        return process.stdout
    except subprocess.CalledProcessError as e:
        log_output(app_instance, f"Error executing command: {e}\\n{e.stderr}")
        return None
    except FileNotFoundError:
        cmd_name = command.split()[0] if isinstance(command, list) else command.split(' ')[0]
        log_output(app_instance, f"Command '{cmd_name}' not found. Please ensure it's in your system's PATH.")
        return None
    except Exception as e:
        log_output(app_instance, f"An unexpected error occurred while running command: {e}")
        return None

def get_report_folder_path(suspect_computer_name, report_name):
    \"\"\"
    Generates the full path for a report file within the suspect's dedicated folder
    on the desktop. Creates the folder if it doesn't exist.
    \"\"\"
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    report_folder = os.path.join(desktop_path, f"{suspect_computer_name} IRIS REPORTS")
    os.makedirs(report_folder, exist_ok=True)
    return os.path.join(report_folder, report_name)

def generate_report_html(app_instance, suspect_computer_name, report_filename, title, html_body, open_in_browser=True):
    \"\"\"
    Generates a full HTML report file with standard styling and optionally opens it in a browser.
    \"\"\"
    report_path = get_report_folder_path(suspect_computer_name, report_filename)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_content = f\"\"\"
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - {suspect_computer_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            h2 {{ color: #0066cc; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; margin-bottom: 20px;}}
            th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
            th {{ background-color: #f2f2f2; }}
            .disallowed-rule {{ color: red; }}
            .active {{ color: #009900; }}
            .inactive {{ color: #FF0000; }}
            pre {{ background-color: #f9f9f9; padding: 10px; border: 1px solid #ddd; white-space: pre-wrap; word-break: break-all; }}
        </style>
    </head>
    <body>
        <h1>{title} - {suspect_computer_name}</h1>
        <p>Report generated on: {current_time}</p>
        {html_body}
    </body>
    </html>
    \"\"\"
    
    try:
        with open(report_path, "w") as f:
            f.write(html_content)
        log_output(app_instance, f"Report generated and saved to: {report_path}")

        if open_in_browser:
            webbrowser.open_new_tab(f"file:///{os.path.abspath(report_path)}")
            log_output(app_instance, f"Opening report in browser: {report_path}")
    except Exception as e:
        log_output(app_instance, f"Error generating or opening report {report_filename}: {e}")
"""

system_diagnostics_content = """
import platform
import sys
import json
import re
import datetime # For timestamps in reports

# Import helpers from the utils package
import IRISX_app.utils.helpers as helpers

def pc_info(app_instance, helpers):
    \"\"\"Gathers and reports general PC information.\"\"\"
    helpers.log_output(app_instance, "\\nRunning PC Info Report...")
    
    html_body = \"\"\"<table><tr><th>Attribute</th><th>Value</th></tr>\"\"\"
    
    # Generic Platform Info
    html_body += f"<tr><td>System</td><td>{platform.system()}</td></tr>"
    html_body += f"<tr><td>Node Name</td><td>{platform.node()}</td></tr>"
    html_body += f"<tr><td>Release</td><td>{platform.release()}</td></tr>"
    html_body += f"<tr><td>Version</td><td>{platform.version()}</td></tr>"
    html_body += f"<tr><td>Machine Architecture</td><td>{platform.machine()}</td></tr>"
    html_body += f"<tr><td>Processor</td><td>{platform.processor()}</td></tr>"

    if sys.platform == "win32":
        # For Windows, use systeminfo or WMIC via subprocess
        helpers.log_output(app_instance, "Gathering detailed Windows system information...")
        output_os = helpers.run_command("systeminfo | findstr /B /C:\"OS Name\" /C:\"OS Version\" /C:\"System Manufacturer\" /C:\"System Model\" /C:\"Processor(s)\" /C:\"Total Physical Memory\"", app_instance=app_instance)
        if output_os:
            for line in output_os.strip().split('\\n'):
                if ":" in line:
                    attr, val = line.split(":", 1)
                    html_body += f"<tr><td>{attr.strip()}</td><td>{val.strip()}</td></tr>"
        
        output_disk = helpers.run_command("wmic diskdrive get Caption,Size", app_instance=app_instance)
        if output_disk:
            html_body += "<tr><th colspan='2'>Disk Drives</th></tr>"
            for line in output_disk.strip().split('\\n')[1:]: # Skip header
                parts = line.strip().split()
                if len(parts) >= 2:
                    caption = " ".join(parts[:-1])
                    try:
                        size_gb = round(int(parts[-1]) / (1024**3), 2)
                        html_body += f"<tr><td>{caption}</td><td>{size_gb} GB</td></tr>"
                    except ValueError:
                        html_body += f"<tr><td>{caption}</td><td>{parts[-1]} (Size Error)</td></tr>"


    elif sys.platform == "darwin":
        # For macOS, use system_profiler
        helpers.log_output(app_instance, "Gathering detailed macOS system information using system_profiler...")
        
        # Hardware Info
        hardware_info = helpers.run_command("system_profiler SPHardwareDataType", check_shell=True, app_instance=app_instance)
        if hardware_info:
            html_body += "<tr><th colspan='2'>Hardware Information</th></tr>"
            for line in hardware_info.strip().split('\\n'):
                if ":" in line and not line.strip().startswith('  '): # Only top-level properties
                    attr, val = line.split(":", 1)
                    html_body += f"<tr><td>{attr.strip()}</td><td>{val.strip()}</td></tr>"

        # Network Info (basic)
        network_info = helpers.run_command("ifconfig", check_shell=True, app_instance=app_instance)
        if network_info:
            html_body += "<tr><th colspan='2'>Network Interfaces (Basic)</th></tr>"
            html_body += f"<tr><td colspan='2'><pre>{network_info}</pre></td></tr>"

    html_body += \"\"\"</table>\"\"\"
    
    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "PCINFO_Report.html", 
        "PC Information Report", 
        html_body
    )

def local_accounts(app_instance, helpers):
    \"\"\"Gathers and reports local user accounts and administrator status.\"\"\"
    helpers.log_output(app_instance, "\\nChecking for Computer Accounts...")
    
    html_body = ""

    if sys.platform == "win32":
        helpers.log_output(app_instance, "Gathering Windows local accounts and profiles...")
        local_users_output = helpers.run_command("net user", check_shell=True, app_instance=app_instance)
        admin_group_output = helpers.run_command("net localgroup Administrators", check_shell=True, app_instance=app_instance)
        
        html_body += "<h3>Local Users (basic output from 'net user'):</h3>"
        if local_users_output:
            html_body += f"<pre>{local_users_output}</pre>"
        html_body += "<h3>Local Administrators (basic output from 'net localgroup Administrators'):</h3>"
        if admin_group_output:
            html_body += f"<pre>{admin_group_output}</pre>"

    elif sys.platform == "darwin":
        helpers.log_output(app_instance, "Gathering macOS local accounts and admin group membership...")
        
        users_list = helpers.run_command("dscl . -list /Users", check_shell=True, app_instance=app_instance)
        if users_list:
            html_body += "<h3>Local User Accounts:</h3><table><tr><th>Username</th><th>Is Admin</th></tr>"
            admin_members_output = helpers.run_command("dscl . -read /Groups/admin GroupMembership", check_shell=True, app_instance=app_instance)
            admin_members = []
            if admin_members_output and "GroupMembership:" in admin_members_output:
                admin_members = admin_members_output.split("GroupMembership:")[1].strip().split()
            
            for user in users_list.strip().split('\\n'):
                is_admin = "Yes" if user.strip() in admin_members else "No"
                html_body += f"<tr><td>{user.strip()}</td><td>{is_admin}</td></tr>"
            html_body += "</table>"
        
        html_body += "<h3>User Home Directories:</h3><table><tr><th>Path</th></tr>"
        home_dirs = helpers.run_command("ls /Users", check_shell=True, app_instance=app_instance)
        if home_dirs:
            for d in home_dirs.strip().split('\\n'):
                html_body += f"<tr><td>/Users/{d.strip()}</td></tr>"
        html_body += "</table>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "UserAccountsAndLocalAdminsReport.html", 
        "User Accounts and Local Admins Report", 
        html_body
    )

def check_malicious_scripts(app_instance, helpers):
    \"\"\"Scans for potentially malicious running scripts based on keywords.\"\"\"
    helpers.log_output(app_instance, "\\nRunning Malicious Script Check....")
    
    html_body = \"\"\"
    <p>This report identifies potentially malicious scripts running on the system by checking for suspicious keywords in process command lines.</p>
    <table><tr><th>PID</th><th>User</th><th>Command Line</th></tr>
    \"\"\"

    if sys.platform == "win32":
        helpers.log_output(app_instance, "Scanning for suspicious PowerShell processes on Windows...")
        script_check_results = helpers.run_command(
            "powershell.exe -Command \\"Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match 'http|https|base64|powershell -e|pwsh -e' } | Select-Object ProcessId, Name, CommandLine | ConvertTo-Json\\"", 
            check_shell=True, app_instance=app_instance
        )
        if script_check_results:
            try:
                processes = json.loads(script_check_results)
                for proc in processes:
                    html_body += f"<tr><td>{proc.get('ProcessId', 'N/A')}</td><td>{proc.get('Name', 'N/A')}</td><td>{proc.get('CommandLine', 'N/A')}</td></tr>"
                html_body += "</table>"
            except json.JSONDecodeError:
                helpers.log_output(app_instance, "Error parsing PowerShell output for malicious script check.")
                html_body += "<tr><td colspan='3' style='color: red;'>Error parsing suspicious script check results.</td></tr></table>"
        else:
            html_body += "<tr><td colspan='3' style='color: green; font-weight: bold;'>No suspicious PowerShell activity detected.</td></tr></table>"

    elif sys.platform == "darwin":
        helpers.log_output(app_instance, "Scanning for suspicious processes on macOS using 'ps aux'...")
        # Common suspicious patterns: base64 encoded commands, direct downloads, unexpected shell scripts
        suspicious_patterns = r"(curl|wget|python -c|perl -e|php -r).*?(http|https)|(base64 -D)"
        
        all_processes = helpers.run_command("ps aux", check_shell=True, app_instance=app_instance)
        if all_processes:
            found_suspicious = False
            for line in all_processes.strip().split('\\n')[1:]: # Skip header
                if re.search(suspicious_patterns, line, re.IGNORECASE):
                    parts = line.strip().split(None, 10) # Split by space, limit to 10 parts for common fields + command
                    if len(parts) >= 11:
                        pid = parts[1]
                        user = parts[0]
                        cmd = " ".join(parts[10:]) # Command line is the rest
                        html_body += f"<tr><td>{pid}</td><td>{user}</td><td>{cmd}</td></tr>"
                        found_suspicious = True
            html_body += "</table>"
            
            if not found_suspicious:
                html_body = html_body.replace("</table>", "<tr><td colspan='3' style='color: green; font-weight: bold;'>No suspicious activity detected on macOS.</td></tr></table>")
        else:
            html_body += "<tr><td colspan='3'>Could not retrieve process list.</td></tr></table>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        f"MaliciousScriptsReport_{datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')}.html", 
        "Potentially Malicious Running Scripts Report", 
        html_body
    )

def running_process(app_instance, helpers):
    \"\"\"Gathers and reports running processes and services.\"\"\"
    helpers.log_output(app_instance, "\\nStarting Running Process Report....")
    
    html_body = ""

    # Running Processes
    html_body += "<h2>Running Processes</h2><table><tr><th>Name</th><th>PID</th><th>User</th></tr>"
    if sys.platform == "win32":
        processes_output = helpers.run_command("powershell.exe -Command \\"Get-Process | Select-Object ProcessName, Id, @{Name='UserName';Expression={$_.Owner}}\\"", app_instance=app_instance)
        if processes_output:
            for line in processes_output.strip().split('\\n')[3:]: # Skip header and separator
                parts = line.strip().split(None, 2)
                if len(parts) == 3:
                    name = parts[0]
                    pid = parts[1]
                    user = parts[2]
                    html_body += f"<tr><td>{name}</td><td>{pid}</td><td>{user}</td></tr>"
        else:
            html_body += "<tr><td colspan='3'>Could not retrieve Windows processes.</td></tr>"
    elif sys.platform == "darwin":
        processes_output = helpers.run_command("ps aux", check_shell=True, app_instance=app_instance)
        if processes_output:
            for line in processes_output.strip().split('\\n')[1:]: # Skip header
                parts = line.strip().split(None, 10) # Split by space, limit to 10 parts for common fields + command
                if len(parts) >= 11:
                    user = parts[0]
                    pid = parts[1]
                    cmd = " ".join(parts[10:]) # Command line is the rest
                    html_body += f"<tr><td>{cmd}</td><td>{pid}</td><td>{user}</td></tr>"
        else:
            html_body += "<tr><td colspan='3'>Could not retrieve macOS processes.</td></tr>"
    html_body += "</table>"

    # Services (Windows-only, for macOS will be LaunchDaemons/Agents)
    html_body += "<h2>Services and Their Status</h2><table><tr><th>Display Name</th><th>Status</th></tr>"
    if sys.platform == "win32":
        services_output = helpers.run_command("powershell.exe -Command \\"Get-Service | Select-Object DisplayName, Status\\"", app_instance=app_instance)
        if services_output:
            for line in services_output.strip().split('\\n')[3:]: # Skip header and separator
                parts = line.strip().rsplit(None, 1) # Split from right, once
                if len(parts) == 2:
                    name = parts[0].strip()
                    status = parts[1].strip()
                    html_body += f"<tr><td>{name}</td><td>{status}</td></tr>"
        else:
            html_body += "<tr><td colspan='2'>Could not retrieve Windows services.</td></tr>"
    elif sys.platform == "darwin":
        helpers.log_output(app_instance, "For macOS, services are typically managed via LaunchDaemons/Agents.")
        launch_daemons = helpers.run_command("sudo launchctl list", check_shell=True, app_instance=app_instance)
        html_body += "<tr><td colspan='2'><b>macOS LaunchDaemons/Agents (partial via `launchctl list`):</b></td></tr>"
        if launch_daemons:
            html_body += f"<tr><td colspan='2'><pre>{launch_daemons}</pre></td></tr>"
        else:
            html_body += "<tr><td colspan='2'>Could not retrieve LaunchDaemons/Agents.</td></tr>"
    html_body += "</table>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "RunningProcessesAndServices.html", 
        "Running Processes and Services Report", 
        html_body
    )

def netstat_connections(app_instance, helpers):
    \"\"\"Gathers and reports active network connections (netstat -an).\"\"\"
    helpers.log_output(app_instance, "\\nStarting Netstat Report...")
    
    html_body = \"\"\"<table><tr><th>Protocol</th><th>Local Address</th><th>Foreign Address</th><th>State</th></tr>\"\"\"
    
    netstat_output = helpers.run_command("netstat -an", app_instance=app_instance)
    if netstat_output:
        for line in netstat_output.strip().split('\\n'):
            # Filter lines that look like connection data (start with Proto)
            if line.strip().startswith(('TCP', 'UDP', 'tcp', 'udp')):
                fields = line.strip().split()
                if len(fields) >= 4: # Ensure enough fields for Protocol, Local, Foreign, State
                    protocol = fields[0]
                    local_address = fields[1]
                    foreign_address = fields[2]
                    state = fields[3] if len(fields) > 3 else "N/A" # State might be missing for UDP
                    html_body += f"<tr><td>{protocol}</td><td>{local_address}</td><td>{foreign_address}</td><td>{state}</td></tr>"
        if not html_body.strip().endswith("</tr>"): # If no connections were added, add a message
            html_body += "<tr><td colspan='4'>No network connections found or permission denied. Try running with elevated privileges.</td></tr>"
    else:
        html_body += "<tr><td colspan='4'>Could not retrieve Netstat output. Try running with elevated privileges.</td></tr>"

    html_body += \"\"\"</table>\"\"\"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "NetstatReport.html", 
        "Netstat Report", 
        html_body
    )
"""

main_app_content = """
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog, messagebox, simpledialog
import platform
import subprocess
import hashlib
import os
import sys
import requests
import re
import json
import shutil 
import datetime 
import webbrowser # Keep for general browser opening, though report opening is centralized

# Import modularized components
import IRISX_app.utils.helpers as helpers
import IRISX_app.modules.system_diagnostics as system_diagnostics

# --- GUI SETUP ---
class IRISApp:
    def __init__(self, master):
        self.master = master
        master.title("IRIS RAPID RESPONSE")
        master.geometry("810x810") # Set form size as in PowerShell
        master.resizable(False, False)
        master.config(bg="") # Background color (can be set to a hex code or color name)

        # Output Box
        self.output_box = ScrolledText(master, width=60, height=20, wrap=tk.WORD)
        self.output_box.place(x=250, y=200)
        self.log_output("WELCOME TO IRIS RAPID RESPONSE:\\n\\n"
                                        "ALL REPORTS WILL GENERATE THEIR OWN HTML FILE IN A FOLDER ON YOUR DESKTOP "
                                        "WITH THE COMPUTER NAME. THIS WAS DESIGNED TO BE RAN AGAINST AN INFECTED "
                                        "OR SUSPECT MACHINE TO HELP GATHER INFORMATION ABOUT AN INCIDENT.\\n\\n"
                                        "GOOD LUCK THREAT HUNTING!\\n\\n- SHIFTY -\\n\\n")

        # Suspect PC Input
        self.suspect_pc_label = tk.Label(master, text="SUSPECT COMPUTER:")
        self.suspect_pc_label.place(x=250, y=175)
        self.suspect_pc_entry = tk.Entry(master, width=30)
        self.suspect_pc_entry.place(x=400, y=175)
        self.suspect_pc_entry.bind("<Return>", self.set_suspect_pc) # Allow Enter key to set

        # Buttons - organized as per your PowerShell script
        # Command functions are now wrapped in lambda to pass 'self' and 'helpers'
        self.create_button("RUN ALL REPORTS", lambda: self.run_all_reports_placeholder(), 70, 200, "yellow", 165, 24)
        self.create_button("PC INFORMATION", lambda: system_diagnostics.pc_info(self, helpers), 70, 240, "whitesmoke", 165, 24)
        self.create_button("USER ACCOUNTS", lambda: system_diagnostics.local_accounts(self, helpers), 70, 280, "whitesmoke", 165, 24)
        self.create_button("FIREWALL RULES", lambda: self.firewall_rules_placeholder(), 70, 320, "whitesmoke", 165, 24)
        self.create_button("TCP CONNECTIONS", lambda: system_diagnostics.netstat_connections(self, helpers), 70, 360, "whitesmoke", 165, 24)
        self.create_button("LOGON REPORT", lambda: self.logon_report_placeholder(), 70, 400, "whitesmoke", 165, 24)
        self.create_button("ANTIVIRUS STATUS", lambda: self.antivirus_placeholder(), 70, 440, "whitesmoke", 165, 24)
        self.create_button("WEB HISTORY", lambda: self.web_history_placeholder(), 70, 480, "whitesmoke", 165, 24)
        self.create_button("SCRIPT CHECK", lambda: system_diagnostics.check_malicious_scripts(self, helpers), 70, 520, "whitesmoke", 165, 24)
        self.create_button("SCHEDULED TASKS", lambda: self.scheduled_tasks_placeholder(), 70, 560, "whitesmoke", 165, 24)
        self.create_button("INSTALLED SOFTWARE", lambda: self.installed_software_placeholder(), 70, 600, "whitesmoke", 165, 24)
        
        self.create_button("USB DEVICE REPORT", lambda: self.usb_device_placeholder(), 250, 600, "whitesmoke", 165, 24)
        self.create_button("STARTUP", lambda: self.startup_placeholder(), 250, 560, "whitesmoke", 165, 24)
        self.create_button("NETWORK REPORT", lambda: self.wifi_network_placeholder(), 250, 520, "whitesmoke", 165, 24)

        self.create_button("RUNNING PROCESSES", lambda: system_diagnostics.running_process(self, helpers), 430, 520, "whitesmoke", 165, 24)
        self.create_button("COMPUTER ACCOUNTS", lambda: self.computer_accounts_placeholder(), 430, 560, "black", 165, 24, fg="white")
        self.create_button("DISABLE NETWORK", lambda: self.disable_network_placeholder(), 430, 600, "firebrick", 165, 24, fg="white")

        self.create_button("Remote C:", lambda: self.remote_c_placeholder(), 620, 595, "whitesmoke", 110, 40)
        self.create_button("SHUTDOWN PC", lambda: self.shutdown_pc_placeholder(), 620, 550, "whitesmoke", 110, 40)
        self.create_button("PING", lambda: self.main_ping(), 620, 505, "blue", 110, 40, fg="white")

        # Top Right Buttons (Browser/User Artifacts)
        self.create_button("Chrome Extension", lambda: self.browserext_placeholder(), 660, 220, 'SystemButtonFace', 125, 40) 
        self.create_button("User Downloads", lambda: self.user_downloads_placeholder(), 660, 270, 'SystemButtonFace', 125, 40)
        self.create_button("Browser Artifacts", lambda: self.browser_artifacts_placeholder(), 660, 320, 'SystemButtonFace', 125, 40)
        self.create_button("Remove Windows Pin/Biometrics", lambda: self.remove_pin_placeholder(), 660, 430, 'SystemButtonFace', 125, 40)

        # Bottom Row Buttons (Investigation Tools)
        self.create_button("MAC Vendor", lambda: self.mac_info(), 10, 650, "lightblue", 110, 24)
        self.create_button("URL Check", lambda: self.tinyurl(), 130, 650, "lightgreen", 110, 24)
        self.create_button("Hash Check", lambda: self.hash_file(), 250, 650, "darkorchid", 110, 24)
        self.create_button("WHOIS", lambda: self.whois_lookup(), 370, 650, "forestgreen", 110, 24)
        self.create_button("EVENT VIEWER REPORT", lambda: self.event_viewer_placeholder(), 490, 650, "white", 70, 50)
        self.create_button("PC Images", lambda: self.image_thumbnails_placeholder(), 570, 650, "white", 70, 50)

        # SQL Related
        self.create_button("DB Browser for SQLite DOWNLOAD (Non-Affiliated Link.)", lambda: self.sqlview_download(), 10, 730, "forestgreen", 200, 65)
        self.create_button("SQL QUERY", lambda: self.sql_query(), 370, 750, "white", 100, 35)

        # Version & Printable Report
        self.create_button("v3.2", lambda: self.show_version(), 750, 770, "whitesmoke", 50, 24)
        self.create_button("Printable Result", lambda: self.IRIS_file_report_placeholder(), 550, 770, "orange", 180, 30)
        
        self.suspect_computer_name = "UNKNOWN" # Default

        # Initial call to set suspect PC, and ping it
        self.update_suspect_pc_display()
        self.get_suspect_pc_on_startup()


    def create_button(self, text, command, x, y, bg, width, height, fg="black"):
        button = tk.Button(self.master, text=text, command=command, bg=bg, fg=fg, width=width // 8, height=height // 15)
        button.place(x=x, y=y, width=width, height=height)
        return button

    def log_output(self, message):
        # Now acts as a wrapper for helpers.log_output, always passing self
        helpers.log_output(self, message) 

    def set_suspect_pc(self, event=None): 
        current_entry = self.suspect_pc_entry.get().strip()
        if current_entry:
            self.suspect_computer_name = current_entry
            self.log_output(f"Suspect Computer set to: {self.suspect_computer_name}")
            self.update_suspect_pc_display()
            self.main_ping() 
        else:
            self.log_output("Please enter a suspect computer name.")

    def get_suspect_pc_on_startup(self):
        computer_name = simpledialog.askstring("IRIS RAPID RESPONSE", "Enter Suspect Computer Name:")
        if computer_name:
            self.suspect_computer_name = computer_name.strip()
            self.log_output(f"Suspect Computer set to: {self.suspect_computer_name}")
            self.update_suspect_pc_display()
            self.main_ping()
        else:
            self.log_output("No suspect computer name entered. Defaulting to 'UNKNOWN'.")
            self.suspect_computer_name = "UNKNOWN"
            self.update_suspect_pc_display()

    def update_suspect_pc_display(self):
        self.suspect_pc_label.config(text=f"SUSPECT COMPUTER: {self.suspect_computer_name}")

    # --- Core Function Implementations (Remaining in main_app for now) ---
    # These will be moved to relevant modules in future steps

    def main_ping(self):
        computer_name = self.suspect_computer_name
        if not computer_name or computer_name == "UNKNOWN":
            self.log_output("Error: Suspect computer name is not set for ping.")
            return

        self.log_output(f"\\nChecking to see if system {computer_name} is still reachable....")
        try:
            if sys.platform == "win32":
                command = ['ping', '-n', '1', computer_name]
            else:
                command = ['ping', '-c', '1', computer_name]
            
            output = helpers.run_command(command, app_instance=self)
            if output:
                if "Reply from" in output or "bytes from" in output:
                    match = re.search(r'time[=<](\\d+\\.?\\d*)ms', output)
                    if match:
                        response_time = match.group(1)
                        self.log_output(f"{computer_name} is reachable. Response time: {response_time} ms")
                    else:
                        self.log_output(f"{computer_name} is reachable.")
                else:
                    self.log_output(f"{computer_name} is unreachable.")
            else:
                self.log_output(f"Failed to execute ping command for {computer_name}.")
        except Exception as e:
            self.log_output(f"An error occurred during ping: {e}")

    def hash_file(self):
        self.log_output("\\nHash Tool Started.")
        file_path = filedialog.askopenfilename(
            title="SELECT A FILE TO GET HASH",
            filetypes=[("All files", "*.*")]
        )
        if file_path:
            self.log_output(f"Selected file: {file_path}")
            try:
                md5_hash = hashlib.md5()
                with open(file_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        md5_hash.update(byte_block)
                self.log_output(f"MD5 Hash: {md5_hash.hexdigest()}")

                sha256_hash = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                self.log_output(f"SHA256 Hash: {sha256_hash.hexdigest()}")

            except FileNotFoundError:
                self.log_output("Error: File not found.")
            except Exception as e:
                self.log_output(f"An error occurred while hashing: {e}")
        else:
            self.log_output("No file selected.")

    def mac_info(self):
        self.log_output("\\nLooking Up MAC Address Vendor Information...")
        mac_address = simpledialog.askstring("MAC Address Lookup", "Please enter a MAC address:", parent=self.master)
        
        if mac_address:
            mac_address = mac_address.replace(":", "").replace("-", "").strip() 
            if not mac_address:
                self.log_output("Invalid MAC address entered.")
                return

            api_url = f"https://api.macvendors.com/{mac_address}"
            try:
                response = requests.get(api_url)
                if response.status_code == 200:
                    self.log_output(f"MAC address information for {mac_address}:")
                    self.log_output(response.text)
                elif response.status_code == 404:
                    self.log_output(f"MAC address {mac_address} not found.")
                else:
                    self.log_output(f"Error fetching MAC address info (Status: {response.status_code}): {response.text}")
            except requests.exceptions.RequestException as e:
                self.log_output(f"Network error during MAC address lookup: {e}")
            except Exception as e:
                self.log_output(f"An unexpected error occurred: {e}")
        else:
            self.log_output("MAC address lookup cancelled.")

    def tinyurl(self):
        self.log_output("\\nURL Check Tool Started.")
        url_shortened = simpledialog.askstring("URL Check", "Enter a shortened URL:", parent=self.master)
        if url_shortened:
            try:
                response = requests.head(url_shortened, allow_redirects=True, timeout=10)
                final_url = response.url
                status_code = response.status_code
                
                self.log_output(f"Result for {url_shortened}:")
                self.log_output(f"Resolved URL: {final_url}")
                self.log_output(f"Status Code: {status_code}")
                vendor = response.headers.get('X-Powered-By', 'N/A')
                self.log_output(f"Vendor (X-Powered-By): {vendor}")
            except requests.exceptions.RequestException as e:
                self.log_output(f"Error fetching URL: {e}")
            except Exception as e:
                self.log_output(f"An unexpected error occurred: {e}")
        else:
            self.log_output("URL check cancelled.")

    def whois_lookup(self):
        self.log_output("\\nOpening WHOIS Tool...")
        ip_or_url = simpledialog.askstring("WHOIS Lookup", "Enter IP Address or URL:", parent=self.master)
        if ip_or_url:
            self.log_output(f"Looking up WHOIS for: {ip_or_url}")
            try:
                response = requests.get(f"http://ip-api.com/json/{ip_or_url}")
                data = response.json()

                output_str = ""
                if data and data.get("status") == "success":
                    for key, value in data.items():
                        output_str += f"{key.replace('_', ' ').title()}: {value}\\n"
                else:
                    output_str = f"Could not retrieve WHOIS information for {ip_or_url}. Status: {data.get('status', 'Unknown')}, Message: {data.get('message', 'N/A')}"
                
                messagebox.showinfo("WHOIS Result", output_str)
                self.log_output("WHOIS lookup complete.")
            except requests.exceptions.RequestException as e:
                self.log_output(f"Network error during WHOIS lookup: {e}")
            except json.JSONDecodeError:
                self.log_output("Error decoding WHOIS API response.")
            except Exception as e:
                self.log_output(f"An unexpected error occurred: {e}")
        else:
            self.log_output("WHOIS lookup cancelled.")

    def sql_query(self):
        query = \"\"\"
SELECT 
    'Browse' AS type,
    urls.url AS item, 
    datetime(visits.visit_time/1000000-11644473600, 'unixepoch', '-7 hours') as visit_time
FROM 
    visits
JOIN 
    urls ON visits.url = urls.id

UNION ALL

SELECT 
    'Download' AS type,
    downloads.target_path AS item, 
    datetime(downloads.start_time/1000000-11644473600, 'unixepoch', '-7 hours') as visit_time
FROM 
    downloads

ORDER BY 
    visit_time ASC;
\"\"\"
        self.master.clipboard_clear()
        self.master.clipboard_append(query)
        self.master.update() 

        messagebox.showinfo("SQL Query Instructions",
                            "The SQL query has been copied to your clipboard.\\n\\n"
                            "Open a SQLite browser (e.g., DB Browser for SQLite), go to the 'Execute SQL' tab, "
                            "paste this query into the input box, and press the 'play' button.\\n\\n"
                            "This query is designed to work with Chrome/Edge/Brave History/Download databases.")
        
        self.log_output("SQL query for browser artifacts copied to clipboard.")

    def sqlview_download(self):
        webbrowser.open("https://sqlitebrowser.org/")
        self.log_output("Opening DB Browser for SQLite download page...")

    def show_version(self):
        messagebox.showinfo("IRIS Rapid Response", "IRIS Rapid Response - Created by Josh Hochstettler\\nv3.2")
        self.log_output("Version information displayed.")

    # --- Placeholder Functions ---
    # These functions are kept in main_app for now but will be moved to relevant modules in future steps.

    def run_all_reports_placeholder(self):
        self.log_output("Running ALL Reports (Placeholder) - This will execute a series of individual reports.")
        
        # Example calls (uncomment and test as you move functions to modules)
        try:
            system_diagnostics.pc_info(self, helpers)
        except Exception as e:
            self.log_output(f"Error running PC Information report: {e}")

        try:
            system_diagnostics.local_accounts(self, helpers)
        except Exception as e:
            self.log_output(f"Error running User Accounts report: {e}")
            
        try:
            system_diagnostics.netstat_connections(self, helpers)
        except Exception as e:
            self.log_output(f"Error running Netstat Connections report: {e}")

        try:
            system_diagnostics.check_malicious_scripts(self, helpers)
        except Exception as e:
            self.log_output(f"Error running Malicious Script Check report: {e}")
        
        try:
            system_diagnostics.running_process(self, helpers)
        except Exception as e:
            self.log_output(f"Error running Running Processes report: {e}")
            
        # ... Add calls to other functions as you implement them ...

        self.IRIS_file_report_placeholder() # Generate the consolidated report at the end
        
        self.log_output("\\nALL Reports process completed. Check the generated HTML files on your desktop.")

    def firewall_rules_placeholder(self):
        helpers.log_output(self, "\\nRunning Firewall Rule Report (Placeholder)...")
        html_body = \"\"\"
        <p>Note: This report might require elevated privileges to run. For remote execution, SSH/WinRM setup is needed.</p>
        <table><tr><th>Rule Name</th><th>Action</th><th>Direction</th><th>Enabled</th><th>Details</th></tr>
        \"\"\"
        if sys.platform == "win32":
            helpers.log_output(self, "Windows: Gathering Windows Firewall rules. This typically involves `powershell.exe -Command \\"Get-NetFirewallRule ...\\"` and parsing JSON output.")
            html_body += "<tr><td colspan='5'>Windows Firewall rules will be gathered here.</td></tr>"
        elif sys.platform == "darwin":
            helpers.log_output(self, "macOS: Gathering macOS Firewall rules using 'socketfilterfw'. This often requires `sudo`.")
            html_body += "<tr><td colspan='5'>macOS Firewall rules will be gathered here. (Requires sudo)</td></tr>"
        html_body += \"\"\"</table>\"\"\"
        helpers.generate_report_html(self, self.suspect_computer_name, "FirewallRulesReport.html", "Firewall Rules Report", html_body)

    def logon_report_placeholder(self):
        helpers.log_output(self, "\\nRunning Logon Report (Placeholder)...")
        html_body = \"\"\"
        <table><tr><th>Time</th><th>User</th><th>Status/Description</th></tr>
        \"\"\"
        if sys.platform == "win32":
            helpers.log_output(self, "Windows: Gathering Logon Events (Event IDs 4624/4625). This is complex parsing of PowerShell `Get-WinEvent` output.")
            html_body += "<tr><td colspan='3'>Windows Logon Events will be gathered here.</td></tr>"
        elif sys.platform == "darwin":
            helpers.log_output(self, "macOS: Gathering Logon History using 'log show' and 'last' commands. This often requires `sudo`.")
            html_body += "<tr><td colspan='3'>macOS Logon History will be gathered here.</td></tr>"
        html_body += \"\"\"</table>\"\"\"
        helpers.generate_report_html(self, self.suspect_computer_name, "LogonReport.html", "Logon Report", html_body)

    def antivirus_placeholder(self):
        helpers.log_output(self, "\\nRunning Antivirus Status Report (Placeholder)...")
        html_body = \"\"\"
        <p>This report will detail Antivirus status and exclusions.</p>
        \"\"\"
        if sys.platform == "win32":
            helpers.log_output(self, "Windows: Querying Microsoft Defender status (`Get-MpComputerStatus`, `Get-MpPreference`) or generic AV via WMI (`root\\\\SecurityCenter2`).")
            html_body += "<p>Windows AV status will be gathered here.</p>"
        elif sys.platform == "darwin":
            helpers.log_output(self, "macOS: Checking common AV application paths and processes (`ps aux`, `ls /Applications`). No centralized AV API.")
            html_body += "<p>macOS AV status will be gathered here.</p>"
        helpers.generate_report_html(self, self.suspect_computer_name, "AntivirusReport.html", "Antivirus Report", html_body)

    def web_history_placeholder(self):
        helpers.log_output(self, "\\nCopying Browser History Database files (Placeholder)...")
        helpers.log_output(self, "This requires identifying browser profile paths, copying SQLite/JSON files (often locked), and parsing them. Remote access needs SSH/WinRM for file transfer.")
        helpers.generate_report_html(self, self.suspect_computer_name, "BrowserHistory_Notes.html", "Browser History Notes", "<p>Notes on browser history collection.</p>")

    def scheduled_tasks_placeholder(self):
        helpers.log_output(self, "\\nGenerating Scheduled Task Report (Placeholder)...")
        html_body = \"\"\"
        <table><tr><th>Task Name</th><th>Status</th><th>Last Run</th><th>Next Run</th></tr>
        \"\"\"
        if sys.platform == "win32":
            helpers.log_output(self, "Windows: Gathering Scheduled Tasks using PowerShell `Get-ScheduledTask`.")
            html_body += "<tr><td>Windows Scheduled Tasks will be gathered here.</td></tr>"
        elif sys.platform == "darwin":
            helpers.log_output(self, "macOS: Gathering LaunchAgents/LaunchDaemons (`launchctl list`) and Cron jobs (`crontab -l`).")
            html_body += "<tr><td>macOS Scheduled Tasks will be gathered here.</td></tr>"
        html_body += \"\"\"</table>\"\"\"
        helpers.generate_report_html(self, self.suspect_computer_name, "ScheduledTasksReport.html", "Scheduled Tasks Report", html_body)

    def installed_software_placeholder(self):
        helpers.log_output(self, "\\nRunning Installed Software Report (Placeholder)...")
        html_body = \"\"\"
        <table><tr><th>Name</th><th>Version</th><th>Publisher</th><th>Install Date</th></tr>
        \"\"\"
        if sys.platform == "win32":
            helpers.log_output(self, "Windows: Gathering Installed Software from Registry keys (Uninstall) or WMI (Win32_Product).")
            html_body += "<tr><td>Windows Installed Software will be gathered here.</td></tr>"
        elif sys.platform == "darwin":
            helpers.log_output(self, "macOS: Gathering Installed Software using `system_profiler SPApplicationsDataType` and listing /Applications.")
            html_body += "<tr><td>macOS Installed Software will be gathered here.</td></tr>"
        html_body += \"\"\"</table>\"\"\"
        helpers.generate_report_html(self, self.suspect_computer_name, "InstalledSoftwareReport.html", "Installed Software Report", html_body)

    def usb_device_placeholder(self):
        helpers.log_output(self, "\\nGetting USB Drive Report (Placeholder)...")
        html_body = \"\"\"
        <table><tr><th>Device Name</th><th>Manufacturer</th><th>Serial</th><th>Status</th></tr>
        \"\"\"
        if sys.platform == "win32":
            helpers.log_output(self, "Windows: Gathering USB devices from `Get-PnpDevice`, WMI, and Registry (for historical).")
            html_body += "<tr><td>Windows USB Device information will be gathered here.</td></tr>"
        elif sys.platform == "darwin":
            helpers.log_output(self, "macOS: Gathering USB devices using `system_profiler SPUSBDataType`.")
            html_body += "<tr><td>macOS USB Device information will be gathered here.</td></tr>"
        html_body += \"\"\"</table>\"\"\"
        helpers.generate_report_html(self, self.suspect_computer_name, "USBDevicesReport.html", "USB Devices Report", html_body)

    def event_viewer_placeholder(self):
        helpers.log_output(self, "\\nPreparing to copy Event Viewer Files (Placeholder)...")
        helpers.log_output(self, "Windows: Copies .evtx files from C:\\\\Windows\\\\System32\\\\Winevt\\\\Logs. macOS: Uses unified logging (`log show`). Remote file transfer is needed.")
        helpers.generate_report_html(self, self.suspect_computer_name, "EventViewer_Notes.html", "Event Viewer/System Log Notes", "<p>Notes on Event Viewer/System Log collection.</p>")

    def browserext_placeholder(self):
        helpers.log_output(self, "\\nRunning Browser Extension identifier tool (Placeholder)...")
        helpers.log_output(self, "This involves locating extension manifest.json files in browser profiles and parsing them. Remote access needs file transfer.")
        helpers.generate_report_html(self, self.suspect_computer_name, "BrowserExtensions_Notes.html", "Browser Extensions Notes", "<p>Notes on browser extension collection.</p>")

    def user_downloads_placeholder(self):
        helpers.log_output(self, "\\nCopying USER Downloads to local Desktop (Placeholder)...")
        helpers.log_output(self, "This copies user Downloads folders. Can transfer large amounts of data. Remote access needs file transfer.")
        helpers.generate_report_html(self, self.suspect_computer_name, "UserDownloads_Notes.html", "User Downloads Notes", "<p>Notes on user downloads collection.</p>")

    def browser_artifacts_placeholder(self):
        helpers.log_output(self, "\\nRunning Browser Artifact Report (Placeholder)...")
        helpers.log_output(self, "Comprehensive report including bookmarks, cookies, cache from browser profiles. Involves SQLite/JSON parsing. Remote access needs file transfer.")
        helpers.generate_report_html(self, self.suspect_computer_name, "BrowserArtifacts_Notes.html", "Browser Artifacts Notes", "<p>Notes on browser artifacts collection.</p>")

    def remove_pin_placeholder(self):
        self.log_output("\\nRemoving Windows Pin/Biometrics (Placeholder) - This is a highly Windows-specific function.")
        self.log_output("This function directly manipulates Windows system files and services related to PIN and Biometric authentication (e.g., NGC folder, WinBioDatabase service).")
        self.log_output("A direct Python equivalent for macOS does not exist. macOS uses different mechanisms for Touch ID, Face ID, and local account passwords.")
        self.log_output("Attempting to implement this for macOS would require in-depth knowledge of macOS security frameworks and potentially undocumented APIs, which is not feasible.")
        self.log_output("For remote Windows, it would require WinRM/PowerShell Remoting with administrative privileges.")
        messagebox.showwarning("Function Not Applicable to macOS", "The 'Remove Windows Pin/Biometrics' function is highly specific to Windows operating systems and cannot be directly translated or implemented for macOS.")

    def remote_c_placeholder(self):
        self.log_output("\\nAccessing Remote C: (Placeholder) - This is a Windows-specific SMB share access.")
        self.log_output("The 'C$' share is an administrative share common on Windows systems.")
        self.log_output("For macOS, accessing a remote share would typically involve mounting an SMB share (e.g., `smb://<computer_name>/C$`) which is handled by the OS, not directly within Python in the same way.")
        self.log_output("Python libraries like 'smbprotocol' could be used for programmatic SMB access, but it's not a direct equivalent to 'Invoke-Item -Path \\\\\\\\$remoteServer\\\\c$'.")
        messagebox.showwarning("Function Not Directly Applicable to macOS", "Accessing a remote C$ share is a Windows-specific operation. For macOS, you would typically use `Finder > Go > Connect to Server...` and enter `smb://<IP_or_Hostname>/C$`.")

    def shutdown_pc_placeholder(self):
        self.log_output("\\nShutting Down PC (Placeholder)...")
        self.log_output("For Windows, this typically uses `Stop-Computer` (PowerShell) or `shutdown /s` (CMD).")
        self.log_output("For macOS, the equivalent local command is `sudo shutdown -h now` or `sudo /sbin/reboot`.")
        self.log_output("Remote execution for both OSes would usually involve SSH (e.g., using 'paramiko' in Python to send the command) and proper authentication/permissions.")
        self.log_output("This is a critical operation; user confirmation and robust error handling are essential.")
        
        if messagebox.askyesno("Confirm Shutdown", f"Are you sure you want to shut down {self.suspect_computer_name}? This action is irreversible remotely and will kill connections.", icon='warning'):
            self.log_output(f"Attempting to shut down {self.suspect_computer_name}...")
            try:
                if sys.platform == "win32":
                    helpers.run_command(f"shutdown /s /f /t 0 /m \\\\\\\\{self.suspect_computer_name}", check_shell=True, app_instance=self)
                elif sys.platform == "darwin":
                    helpers.run_command(f"sudo shutdown -h now", check_shell=True, app_instance=self)
                self.log_output("Shutdown command sent. Verify machine status manually.")
            except Exception as e:
                self.log_output(f"Error attempting to shut down: {e}")
        else:
            self.log_output("Shutdown cancelled by user.")

    def disable_network_placeholder(self):
        self.log_output("\\nDisabling Network Adapters (Placeholder)...")
        self.log_output("For Windows, this uses `Disable-NetAdapter` (PowerShell) or `netsh interface set interface name=\\"Ethernet\\" admin=disable` (CMD).")
        self.log_output("For macOS, the equivalent is `networksetup -setairportpower en0 off` (for Wi-Fi) or `networksetup -setnetworkserviceenabled \\"<service_name>\\" off`.")
        self.log_output("This is a critical operation as it will sever network connectivity. Remote execution would require SSH/WinRM.")
        
        if messagebox.askyesno("Confirm Disable Network", f"WARNING: This will disable network adapters on {self.suspect_computer_name}. You WILL lose connection.", icon='warning'):
            self.log_output(f"Attempting to disable network adapters on {self.suspect_computer_name}...")
            try:
                if sys.platform == "win32":
                    helpers.run_command(f"powershell.exe -Command \\"Get-NetAdapter | Disable-NetAdapter -Confirm:$false\\"", check_shell=True, app_instance=self)
                elif sys.platform == "darwin":
                    helpers.run_command(f"sudo networksetup -setairportpower en0 off", check_shell=True, app_instance=self)
                    helpers.run_command(f"sudo networksetup -setnetworkserviceenabled \\"Ethernet\\" off", check_shell=True, app_instance=self) 
                self.log_output("Network disable command sent. Verify machine status manually.")
            except Exception as e:
                self.log_output(f"Error attempting to disable network: {e}")
        else:
            self.log_output("Network disable cancelled by user.")

    def computer_accounts_placeholder(self):
        self.log_output("\\nOpening Computer Account Tool (Placeholder)...")
        self.log_output("This PowerShell function reads a list of computer names from a file and checks if a specific user's profile folder exists on each. This implies checking remote file shares or using remote execution.")
        self.log_output("For remote Windows, this would involve checking SMB shares (`\\\\\\\\<computer>\\\\C$\\\\Users\\\\<username>`).")
        self.log_output("For remote macOS, this would require SSH and then listing directories (e.g., `ls /Users/<username>`).")
        self.log_output("The 'Test-ComputerOnline' part means performing a ping check, which is already in `main_ping`.")
        
        html_body = "<p>Notes on Computer Accounts Check.</p>"
        helpers.generate_report_html(self, self.suspect_computer_name, "ComputerAccounts_Notes.html", "Computer Accounts Notes", html_body)

    def image_thumbnails_placeholder(self):
        self.log_output("\\nGenerating User Image Reports (Placeholder)...")
        self.log_output("This involves locating user image directories (`Pictures`, `Downloads`, `Recycle Bin`) and generating thumbnails (or base64 encoding images directly into HTML) for a report.")
        self.log_output("Paths vary by OS. For `Recycle Bin`, Windows has specific structure (`$Recycle.Bin`), macOS has `~/.Trash` or `.Trashes`.")
        self.log_output("Copying image files from remote machines requires secure file transfer.")
        
        html_body = "<p>Notes on Image Thumbnails Report.</p>"
        helpers.generate_report_html(self, self.suspect_computer_name, "ImageThumbnails_Notes.html", "Image Thumbnails Notes", html_body)

    def startup_placeholder(self):
        self.log_output("\\nRunning Startup Report (Placeholder)...")
        html_body = \"\"\"
        <table><tr><th>Item</th><th>Command</th><th>Location</th></tr>
        \"\"\"
        if sys.platform == "win32":
            self.log_output("Windows: Gathering Startup Items (Win32_StartupCommand/Registry Run keys).")
            html_body += "<tr><td colspan='3'>Windows Startup Items will be gathered here.</td></tr>"
        elif sys.platform == "darwin":
            self.log_output("macOS: Gathering Startup Items (LaunchAgents/Daemons, Login Items, Cron jobs).")
            html_body += "<tr><td colspan='3'>macOS Startup Items will be gathered here.</td></tr>"
        html_body += \"\"\"</table>\"\"\"
        helpers.generate_report_html(self, self.suspect_computer_name, "StartupReport.html", "Startup Items Report", html_body)

    def wifi_network_placeholder(self):
        self.log_output("\\nRunning WIFI and Network Report (Placeholder)...")
        html_body = \"\"\"
        <table><tr><th>Adapter Name</th><th>MAC Address</th><th>IP Addresses</th><th>Status</th></tr>
        \"\"\"
        if sys.platform == "win32":
            self.log_output("Windows: Gathering Network Adapter info (`Get-NetAdapter`, `ipconfig`). Wi-Fi passwords (`netsh wlan`).")
            html_body += "<tr><td colspan='4'>Windows Network Info will be gathered here.</td></tr>"
        elif sys.platform == "darwin":
            self.log_output("macOS: Gathering Network Adapter info (`networksetup`, `ifconfig`). Wi-Fi passwords are in Keychain (requires sudo).")
            html_body += "<tr><td colspan='4'>macOS Network Info will be gathered here.</td></tr>"
        html_body += \"\"\"</table>\"\"\"
        helpers.generate_report_html(self, self.suspect_computer_name, "NetworkReport.html", "Network Report", html_body)

    def IRIS_file_report_placeholder(self):
        self.log_output("\\nGenerating Printable Result (Placeholder)...")
        self.log_output("This function iterates through all files generated in the IRIS REPORTS folder for the suspect computer.")
        self.log_output("It compiles a list of these files, their creation/modification times, and sizes into a single HTML report for easy printing/review.")
        
        report_folder = helpers.get_report_folder_path(self.suspect_computer_name, "") # Get just the folder path
        
        file_list_html_rows = ""
        try:
            for root, _, files in os.walk(report_folder):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    stat = os.stat(file_path)
                    created_time = datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                    modified_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    size_kb = round(stat.st_size / 1024, 2)
                    
                    display_path = os.path.relpath(file_path, report_folder)
                    file_list_html_rows += f"<tr><td>{display_path}</td><td>{created_time}</td><td>{modified_time}</td><td>{size_kb} KB</td></tr>"
            
            if not file_list_html_rows:
                file_list_html_rows = "<tr><td colspan='4'>No reports generated yet in the IRIS REPORTS folder.</td></tr>"

        except Exception as e:
            self.log_output(f"Error gathering file list for printable report: {e}")
            file_list_html_rows = f"<tr><td colspan='4'>Error gathering file list: {e}</td></tr>"

        html_body = f\"\"\"
        <table>
            <thead>
                <tr><th>File Path</th><th>Date Created</th><th>Date Modified</th><th>Size</th></tr>
            </thead>
            <tbody>
                {file_list_html_rows}
            </tbody>
        </table>
        \"\"\"
        
        # Call the centralized HTML generation function
        helpers.generate_report_html(
            self, 
            self.suspect_computer_name, 
            "Captured File Report.html", 
            "IRIS Captured File Report", 
            html_body
        )


root = tk.Tk()
app = IRISApp(root)
root.mainloop()
"""

# Dictionary to hold file paths and their contents
files_to_create = {
    app_path / "main_app.py": main_app_content,
    utils_path / "helpers.py": helpers_content,
    modules_path / "system_diagnostics.py": system_diagnostics_content,
}

# Create directories and files
def create_project_structure():
    print(f"Attempting to create project structure at: {app_path}")
    
    # Create main app directory
    os.makedirs(app_path, exist_ok=True)
    print(f"Created directory: {app_path}")
    
    # Create subdirectories
    os.makedirs(utils_path, exist_ok=True)
    print(f"Created directory: {utils_path}")
    os.makedirs(modules_path, exist_ok=True)
    print(f"Created directory: {modules_path}")

    # Create __init__.py files to make them Python packages
    (utils_path / "__init__.py").touch(exist_ok=True)
    (modules_path / "__init__.py").touch(exist_ok=True)
    print("Created __init__.py files.")

    # Create and populate .py files
    for file_path, content in files_to_create.items():
        try:
            with open(file_path, "w") as f:
                f.write(content)
            print(f"Created and populated file: {file_path}")
        except Exception as e:
            print(f"Error creating/populating {file_path}: {e}")

if __name__ == "__main__":
    create_project_structure()
    print("\nProject structure generation complete!")
    print(f"You can now run your main application from: {app_path / 'main_app.py'}")
    print("Example: python3 /Users/spencer/Projects/python/IRISX_app/main_app.py")