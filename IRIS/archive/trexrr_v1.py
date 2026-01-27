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
import shutil # For file operations like copying
import datetime # Added for datetime.datetime.now()

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
        self.output_box.insert(tk.END, "WELCOME TO IRIS RAPID RESPONSE:\n\n"
                                        "ALL REPORTS WILL GENERATE THEIR OWN HTML FILE IN A FOLDER ON YOUR DESKTOP "
                                        "WITH THE COMPUTER NAME. THIS WAS DESIGNED TO BE RAN AGAINST AN INFECTED "
                                        "OR SUSPECT MACHINE TO HELP GATHER INFORMATION ABOUT AN INCIDENT.\n\n"
                                        "GOOD LUCK THREAT HUNTING!\n\n- SHIFTY -\n\n")

        # Suspect PC Input
        self.suspect_pc_label = tk.Label(master, text="SUSPECT COMPUTER:")
        self.suspect_pc_label.place(x=250, y=175)
        self.suspect_pc_entry = tk.Entry(master, width=30)
        self.suspect_pc_entry.place(x=400, y=175)
        self.suspect_pc_entry.bind("<Return>", self.set_suspect_pc) # Allow Enter key to set

        # Buttons - organized as per your PowerShell script
        # Column 1 (Left Side Buttons)
        self.create_button("RUN ALL REPORTS", self.run_all_reports_placeholder, 70, 200, "yellow", 165, 24)
        self.create_button("PC INFORMATION", self.pc_info, 70, 240, "whitesmoke", 165, 24)
        self.create_button("USER ACCOUNTS", self.local_accounts, 70, 280, "whitesmoke", 165, 24)
        self.create_button("FIREWALL RULES", self.firewall_rules_placeholder, 70, 320, "whitesmoke", 165, 24)
        self.create_button("TCP CONNECTIONS", self.netstat_connections, 70, 360, "whitesmoke", 165, 24)
        self.create_button("LOGON REPORT", self.logon_report_placeholder, 70, 400, "whitesmoke", 165, 24)
        self.create_button("ANTIVIRUS STATUS", self.antivirus_placeholder, 70, 440, "whitesmoke", 165, 24)
        self.create_button("WEB HISTORY", self.web_history_placeholder, 70, 480, "whitesmoke", 165, 24)
        self.create_button("SCRIPT CHECK", self.check_malicious_scripts, 70, 520, "whitesmoke", 165, 24)
        self.create_button("SCHEDULED TASKS", self.scheduled_tasks_placeholder, 70, 560, "whitesmoke", 165, 24)
        self.create_button("INSTALLED SOFTWARE", self.installed_software_placeholder, 70, 600, "whitesmoke", 165, 24)
        
        # Column 2 (Middle-Left Buttons)
        self.create_button("USB DEVICE REPORT", self.usb_device_placeholder, 250, 600, "whitesmoke", 165, 24)
        self.create_button("STARTUP", self.startup_placeholder, 250, 560, "whitesmoke", 165, 24)
        self.create_button("NETWORK REPORT", self.wifi_network_placeholder, 250, 520, "whitesmoke", 165, 24)

        # Column 3 (Middle-Right Buttons)
        self.create_button("RUNNING PROCESSES", self.running_process, 430, 520, "whitesmoke", 165, 24)
        self.create_button("COMPUTER ACCOUNTS", self.computer_accounts_placeholder, 430, 560, "black", 165, 24, fg="white")
        self.create_button("DISABLE NETWORK", self.disable_network_placeholder, 430, 600, "firebrick", 165, 24, fg="white")

        # Column 4 (Right Side Buttons)
        self.create_button("Remote C:", self.remote_c_placeholder, 620, 595, "whitesmoke", 110, 40)
        self.create_button("SHUTDOWN PC", self.shutdown_pc_placeholder, 620, 550, "whitesmoke", 110, 40)
        self.create_button("PING", self.main_ping, 620, 505, "blue", 110, 40, fg="white")

        # Top Right Buttons (Browser/User Artifacts)
        # Replaced "" with valid color name 'SystemButtonFace'
        self.create_button("Chrome Extension", self.browserext_placeholder, 660, 220, 'SystemButtonFace', 125, 40) 
        self.create_button("User Downloads", self.user_downloads_placeholder, 660, 270, 'SystemButtonFace', 125, 40)
        self.create_button("Browser Artifacts", self.browser_artifacts_placeholder, 660, 320, 'SystemButtonFace', 125, 40)
        self.create_button("Remove Windows Pin/Biometrics", self.remove_pin_placeholder, 660, 430, 'SystemButtonFace', 125, 40)

        # Bottom Row Buttons (Investigation Tools)
        self.create_button("MAC Vendor", self.mac_info, 10, 650, "lightblue", 110, 24)
        self.create_button("URL Check", self.tinyurl, 130, 650, "lightgreen", 110, 24)
        self.create_button("Hash Check", self.hash_file, 250, 650, "darkorchid", 110, 24)
        self.create_button("WHOIS", self.whois_lookup, 370, 650, "forestgreen", 110, 24)
        self.create_button("EVENT VIEWER REPORT", self.event_viewer_placeholder, 490, 650, "white", 70, 50)
        self.create_button("PC Images", self.image_thumbnails_placeholder, 570, 650, "white", 70, 50)

        # SQL Related
        self.create_button("DB Browser for SQLite DOWNLOAD (Non-Affiliated Link.)", self.sqlview_download, 10, 730, "forestgreen", 200, 65)
        self.create_button("SQL QUERY", self.sql_query, 370, 750, "white", 100, 35)

        # Version & Printable Report
        self.create_button("v3.2", self.show_version, 750, 770, "whitesmoke", 50, 24)
        self.create_button("Printable Result", self.IRIS_file_report_placeholder, 550, 770, "orange", 180, 30)
        
        self.suspect_computer_name = "UNKNOWN" # Default

        # Initial call to set suspect PC, and ping it
        self.update_suspect_pc_display()
        self.get_suspect_pc_on_startup()

    def create_button(self, text, command, x, y, bg, width, height, fg="black"):
        button = tk.Button(self.master, text=text, command=command, bg=bg, fg=fg, width=width // 8, height=height // 15)
        button.place(x=x, y=y, width=width, height=height)
        return button

    def log_output(self, message):
        self.output_box.insert(tk.END, message + "\n")
        self.output_box.see(tk.END) # Scroll to end

    def set_suspect_pc(self, event=None): # event=None for binding to button/enter
        current_entry = self.suspect_pc_entry.get().strip()
        if current_entry:
            self.suspect_computer_name = current_entry
            self.log_output(f"Suspect Computer set to: {self.suspect_computer_name}")
            self.update_suspect_pc_display()
            self.main_ping() # Ping the new suspect PC
        else:
            self.log_output("Please enter a suspect computer name.")

    def get_suspect_pc_on_startup(self):
        # This function acts as the initial SuspectPC dialog from PowerShell
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
        # Update the label with the current suspect computer name
        self.suspect_pc_label.config(text=f"SUSPECT COMPUTER: {self.suspect_computer_name}")

    def run_command(self, command, check_shell=False):
        """Helper to run shell commands and capture output."""
        try:
            if sys.platform == "win32" and check_shell:
                 # On Windows, some commands might need powershell.exe or cmd.exe explicitly
                process = subprocess.run(["powershell.exe", "-Command", command], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
            else:
                process = subprocess.run(command, capture_output=True, text=True, check=True, shell=check_shell)
            return process.stdout
        except subprocess.CalledProcessError as e:
            self.log_output(f"Error executing command: {e}\n{e.stderr}")
            return None
        except FileNotFoundError:
            self.log_output(f"Command not found. Please ensure it's in your system's PATH: {command.split()[0] if isinstance(command, list) else command.split(' ')[0]}")
            return None
        except Exception as e:
            self.log_output(f"An unexpected error occurred: {e}")
            return None

    def get_report_folder_path(self, report_name):
        """Helper to get and create report folder path."""
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        report_folder = os.path.join(desktop_path, f"{self.suspect_computer_name} IRIS REPORTS")
        os.makedirs(report_folder, exist_ok=True)
        return os.path.join(report_folder, report_name)

    # --- Core Function Implementations ---

    def main_ping(self):
        computer_name = self.suspect_computer_name
        if not computer_name or computer_name == "UNKNOWN":
            self.log_output("Error: Suspect computer name is not set for ping.")
            return

        self.log_output(f"\nChecking to see if system {computer_name} is still reachable....")
        try:
            if sys.platform == "win32":
                command = ['ping', '-n', '1', computer_name]
            else:
                command = ['ping', '-c', '1', computer_name]
            
            output = self.run_command(command)
            if output:
                if "Reply from" in output or "bytes from" in output:
                    match = re.search(r'time[=<](\d+\.?\d*)ms', output)
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
        self.log_output("\nHash Tool Started.")
        file_path = filedialog.askopenfilename(
            title="SELECT A FILE TO GET HASH",
            filetypes=[("All files", "*.*")]
        )
        if file_path:
            self.log_output(f"Selected file: {file_path}")
            try:
                # Calculate MD5 hash
                md5_hash = hashlib.md5()
                with open(file_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        md5_hash.update(byte_block)
                self.log_output(f"MD5 Hash: {md5_hash.hexdigest()}")

                # Calculate SHA256 hash
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
        self.log_output("\nLooking Up MAC Address Vendor Information...")
        mac_address = simpledialog.askstring("MAC Address Lookup", "Please enter a MAC address:", parent=self.master)
        
        if mac_address:
            mac_address = mac_address.replace(":", "").replace("-", "").strip() # Clean input
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
        self.log_output("\nURL Check Tool Started.")
        url_shortened = simpledialog.askstring("URL Check", "Enter a shortened URL:", parent=self.master)
        if url_shortened:
            try:
                response = requests.head(url_shortened, allow_redirects=True, timeout=10)
                final_url = response.url
                status_code = response.status_code
                
                self.log_output(f"Result for {url_shortened}:")
                self.log_output(f"Resolved URL: {final_url}")
                self.log_output(f"Status Code: {status_code}")
                # Attempt to get X-Powered-By if available (might not be for all services)
                vendor = response.headers.get('X-Powered-By', 'N/A')
                self.log_output(f"Vendor (X-Powered-By): {vendor}")
            except requests.exceptions.RequestException as e:
                self.log_output(f"Error fetching URL: {e}")
            except Exception as e:
                self.log_output(f"An unexpected error occurred: {e}")
        else:
            self.log_output("URL check cancelled.")

    def whois_lookup(self):
        self.log_output("\nOpening WHOIS Tool...")
        ip_or_url = simpledialog.askstring("WHOIS Lookup", "Enter IP Address or URL:", parent=self.master)
        if ip_or_url:
            self.log_output(f"Looking up WHOIS for: {ip_or_url}")
            try:
                # Basic WHOIS lookup via a public API (e.g., ip-api.com)
                response = requests.get(f"http://ip-api.com/json/{ip_or_url}")
                data = response.json()

                output_str = ""
                if data and data.get("status") == "success":
                    for key, value in data.items():
                        output_str += f"{key.replace('_', ' ').title()}: {value}\n"
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
        query = """
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
"""
        # Copy query to clipboard
        self.master.clipboard_clear()
        self.master.clipboard_append(query)
        self.master.update() # Required for clipboard to update

        messagebox.showinfo("SQL Query Instructions",
                            "The SQL query has been copied to your clipboard.\n\n"
                            "Open a SQLite browser (e.g., DB Browser for SQLite), go to the 'Execute SQL' tab, "
                            "paste this query into the input box, and press the 'play' button.\n\n"
                            "This query is designed to work with Chrome/Edge/Brave History/Download databases.")
        
        self.log_output("SQL query for browser artifacts copied to clipboard.")

    def sqlview_download(self):
        import webbrowser
        self.log_output("Opening DB Browser for SQLite download page...")
        webbrowser.open("https://sqlitebrowser.org/")

    def show_version(self):
        messagebox.showinfo("IRIS Rapid Response", "IRIS Rapid Response - Created by Josh Hochstettler\nv3.2")
        self.log_output("Version information displayed.")

    # --- Expanded Function Implementations ---
    def pc_info(self):
        self.log_output("\nRunning PC Info Report...")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_path = self.get_report_folder_path("PCINFO_Report.html")

        html_content = f"""
        <html>
        <head>
            <title>PC Information Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>PC Information Report - {self.suspect_computer_name} - {current_time}</h1>
            <table>
                <tr><th>Attribute</th><th>Value</th></tr>
        """
        
        # Generic Platform Info
        html_content += f"<tr><td>System</td><td>{platform.system()}</td></tr>"
        html_content += f"<tr><td>Node Name</td><td>{platform.node()}</td></tr>"
        html_content += f"<tr><td>Release</td><td>{platform.release()}</td></tr>"
        html_content += f"<tr><td>Version</td><td>{platform.version()}</td></tr>"
        html_content += f"<tr><td>Machine Architecture</td><td>{platform.machine()}</td></tr>"
        html_content += f"<tr><td>Processor</td><td>{platform.processor()}</td></tr>"

        if sys.platform == "win32":
            # For Windows, use systeminfo or WMIC via subprocess
            self.log_output("Gathering detailed Windows system information...")
            output_os = self.run_command("systeminfo | findstr /B /C:\"OS Name\" /C:\"OS Version\" /C:\"System Manufacturer\" /C:\"System Model\" /C:\"Processor(s)\" /C:\"Total Physical Memory\"")
            if output_os:
                for line in output_os.strip().split('\n'):
                    if ":" in line:
                        attr, val = line.split(":", 1)
                        html_content += f"<tr><td>{attr.strip()}</td><td>{val.strip()}</td></tr>"
            
            output_disk = self.run_command("wmic diskdrive get Caption,Size")
            if output_disk:
                html_content += "<tr><th colspan='2'>Disk Drives</th></tr>"
                for line in output_disk.strip().split('\n')[1:]: # Skip header
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        caption = " ".join(parts[:-1])
                        size_gb = round(int(parts[-1]) / (1024**3), 2)
                        html_content += f"<tr><td>{caption}</td><td>{size_gb} GB</td></tr>"

        elif sys.platform == "darwin":
            # For macOS, use system_profiler
            self.log_output("Gathering detailed macOS system information using system_profiler...")
            
            # Hardware Info
            hardware_info = self.run_command("system_profiler SPHardwareDataType", check_shell=True)
            if hardware_info:
                html_content += "<tr><th colspan='2'>Hardware Information</th></tr>"
                for line in hardware_info.strip().split('\n'):
                    if ":" in line and not line.strip().startswith('  '): # Only top-level properties
                        attr, val = line.split(":", 1)
                        html_content += f"<tr><td>{attr.strip()}</td><td>{val.strip()}</td></tr>"

            # Network Info (basic)
            network_info = self.run_command("ifconfig", check_shell=True)
            if network_info:
                html_content += "<tr><th colspan='2'>Network Interfaces (Basic)</th></tr>"
                # This parsing is very basic; a more robust solution would be needed
                html_content += f"<tr><td colspan='2'><pre>{network_info}</pre></td></tr>"

        html_content += """
            </table>
        </body>
        </html>
        """
        
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"PC Info Report generated and saved to: {report_path}")

    def local_accounts(self):
        self.log_output("\nChecking for Computer Accounts...")
        report_path = self.get_report_folder_path("UserAccountsAndLocalAdminsReport.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <html>
        <head>
            <title>User Accounts and Local Admins Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>User Accounts and Local Admins Report - {self.suspect_computer_name}</h1>
            <p>Report generated on: {current_time}</p>
        """

        if sys.platform == "win32":
            # Windows: Get-LocalUser, Get-LocalGroup, Get-WmiObject Win32_NetworkLoginProfile
            self.log_output("Gathering Windows local accounts and profiles...")
            # For remote Windows, Invoke-Command is needed. For local, direct execution.
            # Example using local execution for illustration:
            local_users_output = self.run_command("net user", check_shell=True)
            admin_group_output = self.run_command("net localgroup Administrators", check_shell=True)
            
            html_content += "<h3>Local Users (basic output from 'net user'):</h3>"
            if local_users_output:
                html_content += f"<pre>{local_users_output}</pre>"
            html_content += "<h3>Local Administrators (basic output from 'net localgroup Administrators'):</h3>"
            if admin_group_output:
                html_content += f"<pre>{admin_group_output}</pre>"

        elif sys.platform == "darwin":
            # macOS: dscl . -list /Users, dscl . -read /Groups/admin GroupMembership
            self.log_output("Gathering macOS local accounts and admin group membership...")
            
            users_list = self.run_command("dscl . -list /Users", check_shell=True)
            if users_list:
                html_content += "<h3>Local User Accounts:</h3><table><tr><th>Username</th><th>Is Admin</th></tr>"
                admin_members_output = self.run_command("dscl . -read /Groups/admin GroupMembership", check_shell=True)
                admin_members = []
                if admin_members_output and "GroupMembership:" in admin_members_output:
                    admin_members = admin_members_output.split("GroupMembership:")[1].strip().split()
                
                for user in users_list.strip().split('\n'):
                    is_admin = "Yes" if user.strip() in admin_members else "No"
                    html_content += f"<tr><td>{user.strip()}</td><td>{is_admin}</td></tr>"
                html_content += "</table>"
            
            # User profiles (listing home directories)
            html_content += "<h3>User Home Directories:</h3><table><tr><th>Path</th></tr>"
            home_dirs = self.run_command("ls /Users", check_shell=True)
            if home_dirs:
                for d in home_dirs.strip().split('\n'):
                    html_content += f"<tr><td>/Users/{d.strip()}</td></tr>"
            html_content += "</table>"

        html_content += """
        </body>
        </html>
        """
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"User Accounts Report completed. The Report is saved to: {report_path}")

    def check_malicious_scripts(self):
        self.log_output("\nRunning Malicious Script Check....")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        report_path = self.get_report_folder_path(f"MaliciousScriptsReport_{current_time}.html")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Potentially Malicious Running Scripts Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: red; }}
                h2 {{ color: black; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Potentially Malicious Running Scripts Report</h1>
            <h2>Computer: {self.suspect_computer_name}</h2>
            <h2>Date & Time: {current_time}</h2>
            <p>This report identifies potentially malicious scripts running on the system by checking for suspicious keywords in process command lines.</p>
        """

        if sys.platform == "win32":
            self.log_output("Scanning for suspicious PowerShell processes on Windows...")
            script_check_results = self.run_command(
                "powershell.exe -Command \"Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match 'http|https|base64|powershell -e|pwsh -e' } | Select-Object ProcessId, Name, CommandLine | ConvertTo-Json\"", 
                check_shell=True
            )
            if script_check_results:
                try:
                    processes = json.loads(script_check_results)
                    html_content += "<table><tr><th>Process ID</th><th>Name</th><th>Command Line</th></tr>"
                    for proc in processes:
                        html_content += f"<tr><td>{proc.get('ProcessId', 'N/A')}</td><td>{proc.get('Name', 'N/A')}</td><td>{proc.get('CommandLine', 'N/A')}</td></tr>"
                    html_content += "</table>"
                    self.log_output(f"Suspicious activity detected! Report saved to: {report_path}")
                except json.JSONDecodeError:
                    self.log_output("Error parsing PowerShell output for malicious script check.")
                    html_content += "<p style='color: red;'>Error parsing suspicious script check results.</p>"
            else:
                html_content += "<p style='color: green; font-weight: bold;'>No suspicious PowerShell activity detected.</p>"
                self.log_output(f"No suspicious activity found on {self.suspect_computer_name}.")

        elif sys.platform == "darwin":
            self.log_output("Scanning for suspicious processes on macOS using 'ps aux'...")
            # Common suspicious patterns: base64 encoded commands, direct downloads, unexpected shell scripts
            suspicious_patterns = r"(curl|wget|python -c|perl -e|php -r).*?(http|https)|(base64 -D)"
            
            all_processes = self.run_command("ps aux", check_shell=True)
            if all_processes:
                found_suspicious = False
                html_content += "<table><tr><th>PID</th><th>User</th><th>Command Line</th></tr>"
                for line in all_processes.strip().split('\n')[1:]: # Skip header
                    if re.search(suspicious_patterns, line, re.IGNORECASE):
                        parts = line.strip().split(None, 10) # Split by space, limit to 10 parts for common fields + command
                        if len(parts) >= 11:
                            pid = parts[1]
                            user = parts[0]
                            cmd = " ".join(parts[10:]) # Command line is the rest
                            html_content += f"<tr><td>{pid}</td><td>{user}</td><td>{cmd}</td></tr>"
                            found_suspicious = True
                html_content += "</table>"
                
                if found_suspicious:
                    self.log_output(f"Suspicious activity detected! Report saved to: {report_path}")
                else:
                    html_content += "<p style='color: green; font-weight: bold;'>No suspicious activity detected on macOS.</p>"
                    self.log_output(f"No suspicious activity found on {self.suspect_computer_name}.")

        html_content += "</body></html>"
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"Malicious Script Check completed. Report saved to: {report_path}")

    def running_process(self):
        self.log_output("\nStarting Running Process Report....")
        report_path = self.get_report_folder_path("RunningProcessesAndServices.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <html>
        <head>
            <title>Running Processes and Services - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Running Processes and Services on {self.suspect_computer_name}</h1>
            <h2>Date and Time: {current_time}</h2>
            <hr/>
        """

        # Running Processes
        html_content += "<h2>Running Processes</h2><table><tr><th>Name</th><th>PID</th><th>User</th></tr>"
        if sys.platform == "win32":
            processes_output = self.run_command("powershell.exe -Command \"Get-Process | Select-Object ProcessName, Id, @{Name='UserName';Expression={$_.Owner}}\"")
            if processes_output:
                for line in processes_output.strip().split('\n')[3:]: # Skip header and separator
                    parts = line.strip().split(None, 2)
                    if len(parts) == 3:
                        name = parts[0]
                        pid = parts[1]
                        user = parts[2]
                        html_content += f"<tr><td>{name}</td><td>{pid}</td><td>{user}</td></tr>"
        elif sys.platform == "darwin":
            processes_output = self.run_command("ps aux", check_shell=True)
            if processes_output:
                for line in processes_output.strip().split('\n')[1:]: # Skip header
                    parts = line.strip().split(None, 10) # Split by space, limit to 10 parts for common fields + command
                    if len(parts) >= 11:
                        user = parts[0]
                        pid = parts[1]
                        cmd = " ".join(parts[10:]) # Command line is the rest
                        html_content += f"<tr><td>{cmd}</td><td>{pid}</td><td>{user}</td></tr>"
        html_content += "</table>"

        # Services (Windows-only, for macOS will be LaunchDaemons/Agents)
        html_content += "<h2>Services and Their Status</h2><table><tr><th>Display Name</th><th>Status</th></tr>"
        if sys.platform == "win32":
            services_output = self.run_command("powershell.exe -Command \"Get-Service | Select-Object DisplayName, Status\"")
            if services_output:
                for line in services_output.strip().split('\n')[3:]: # Skip header and separator
                    parts = line.strip().rsplit(None, 1) # Split from right, once
                    if len(parts) == 2:
                        name = parts[0].strip()
                        status = parts[1].strip()
                        html_content += f"<tr><td>{name}</td><td>{status}</td></tr>"
        elif sys.platform == "darwin":
            self.log_output("For macOS, services are typically managed via LaunchDaemons/Agents.")
            launch_daemons = self.run_command("sudo launchctl list", check_shell=True)
            html_content += "<tr><td colspan='2'><b>macOS LaunchDaemons/Agents (partial via `launchctl list`):</b></td></tr>"
            if launch_daemons:
                html_content += f"<tr><td colspan='2'><pre>{launch_daemons}</pre></td></tr>"
            else:
                html_content += "<tr><td colspan='2'>Could not retrieve LaunchDaemons/Agents.</td></tr>"

        html_content += """
        </body>
        </html>
        """
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"Running Process Report completed. HTML file created at: {report_path}")

    def netstat_connections(self):
        self.log_output("\nStarting Netstat Report...")
        report_path = self.get_report_folder_path("NetstatReport.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Netstat Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Netstat Report - {self.suspect_computer_name}</h1>
            <p>Generated on: {current_time}</p>
            <table>
                <tr><th>Protocol</th><th>Local Address</th><th>Foreign Address</th><th>State</th></tr>
        """
        
        netstat_output = self.run_command("netstat -an")
        if netstat_output:
            for line in netstat_output.strip().split('\n'):
                # Filter lines that look like connection data (start with Proto)
                if line.strip().startswith(('TCP', 'UDP', 'tcp', 'udp')):
                    fields = line.strip().split()
                    if len(fields) >= 4: # Ensure enough fields for Protocol, Local, Foreign, State
                        protocol = fields[0]
                        local_address = fields[1]
                        foreign_address = fields[2]
                        state = fields[3] if len(fields) > 3 else "N/A" # State might be missing for UDP
                        html_content += f"<tr><td>{protocol}</td><td>{local_address}</td><td>{foreign_address}</td><td>{state}</td></tr>"
        html_content += """
            </table>
        </body>
        </html>
        """
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"Netstat Report completed. The Report is saved to: {report_path}")

    # --- Placeholder Functions with Conceptual Explanation ---

    def run_all_reports_placeholder(self):
        self.log_output("Running ALL Reports (Placeholder) - This will execute a series of individual reports.")
        # This would call all the other implemented functions sequentially.
        # Example:
        # self.pc_info()
        # self.local_accounts()
        # self.firewall_rules_placeholder() # And so on for all relevant reports

    def firewall_rules_placeholder(self):
        self.log_output("\nRunning Firewall Rule Report (Placeholder)...")
        report_path = self.get_report_folder_path("FirewallRulesReport.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <html>
        <head>
            <title>Firewall Rules Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
                .disallowed-rule {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>Firewall Rules Report - {self.suspect_computer_name}</h1>
            <p>Report Date and Time: {current_time}</p>
            <p>Note: This report might require elevated privileges to run. For remote execution, SSH/WinRM setup is needed.</p>
            <table>
                <tr><th>Rule Name</th><th>Action</th><th>Direction</th><th>Enabled</th><th>Details</th></tr>
        """
        
        if sys.platform == "win32":
            self.log_output("Gathering Windows Firewall rules...")
            powershell_command = "Get-NetFirewallRule | Select-Object DisplayName, Action, Direction, Enabled, @{Name='LocalAddress';Expression={$_.LocalAddress -join ','}}, @{Name='RemoteAddress';Expression={$_.RemoteAddress -join ','}}, Protocol, @{Name='LocalPort';Expression={$_.LocalPort -join ','}}, @{Name='RemotePort';Expression={$_.RemotePort -join ','}}, Program, Service | ConvertTo-Json"
            rules_json = self.run_command(powershell_command, check_shell=True)
            
            if rules_json:
                try:
                    rules = json.loads(rules)
                    for rule in rules:
                        disallowed_class = " class='disallowed-rule'" if rule.get('Action') == 'Block' and rule.get('Enabled') else ""
                        html_content += f"<tr{disallowed_class}><td>{rule.get('DisplayName', 'N/A')}</td><td>{rule.get('Action', 'N/A')}</td><td>{rule.get('Direction', 'N/A')}</td><td>{rule.get('Enabled', 'N/A')}</td><td>Local: {rule.get('LocalAddress', 'N/A')}, Remote: {rule.get('RemoteAddress', 'N/A')}, Proto: {rule.get('Protocol', 'N/A')}, LPort: {rule.get('LocalPort', 'N/A')}, RPort: {rule.get('RemotePort', 'N/A')}, Program: {rule.get('Program', 'N/A')}, Service: {rule.get('Service', 'N/A')}</td></tr>"
                except json.JSONDecodeError:
                    self.log_output("Error parsing PowerShell output for firewall rules.")
            else:
                html_content += "<tr><td colspan='5'>Could not retrieve Windows Firewall rules. Ensure PowerShell is accessible and correct modules are loaded.</td></tr>"

        elif sys.platform == "darwin":
            self.log_output("Gathering macOS Firewall rules using 'socketfilterfw'...")
            try:
                global_state = self.run_command("sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate", check_shell=True)
                app_blocked = self.run_command("sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getappblocked", check_shell=True)
                all_rules = self.run_command("sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listall", check_shell=True)

                html_content += f"<tr><td colspan='5'><b>Global State:</b> {global_state.strip()}</td></tr>"
                html_content += f"<tr><td colspan='5'><b>Blocked Applications:</b> {app_blocked.strip()}</td></tr>"
                html_content += "<tr><td colspan='5'><b>All Firewall Rules:</b><pre>"
                if all_rules: html_content += all_rules
                html_content += "</pre></td></tr>"
            except Exception as e:
                self.log_output(f"Error retrieving macOS firewall rules: {e}. You might need to run the script with 'sudo'.")
                html_content += "<tr><td colspan='5'>Could not retrieve macOS firewall rules. Ensure you have permissions or run with sudo.</td></tr>"
        
        html_content += """
            </table>
        </body>
        </html>
        """
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"Firewall Rule Report completed. The Report is saved to: {report_path}")

    def logon_report_placeholder(self):
        self.log_output("\nRunning Logon Report (Placeholder)...")
        report_path = self.get_report_folder_path("LogonReport.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <html>
        <head>
            <title>Logon Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
                .failed-login {{ color: #cc0000; }}
            </style>
        </head>
        <body>
            <h1>Logon Report - {self.suspect_computer_name}</h1>
            <p>Report generated on: {current_time}</p>
            <table>
                <tr><th>Time</th><th>User</th><th>Status/Description</th></tr>
        """
        if sys.platform == "win32":
            self.log_output("Gathering Windows Logon Events (Event IDs 4624/4625)...")
            html_content += "<tr><td colspan='3'>Windows: Retrieving logon events via PowerShell's Get-WinEvent. This can be complex to parse directly in Python. Consider exporting logs to EVTX and parsing offline.</td></tr>"
            html_content += "<tr><td colspan='3'>You would typically run: `powershell.exe -Command \"Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4624,4625} | Select-Object TimeCreated, @{N='User';E={$_.Properties[5].Value}}, @{N='LogonType';E={$_.Properties[8].Value}} | ConvertTo-Json\"` and parse the JSON.</td></tr>"
        elif sys.platform == "darwin":
            self.log_output("Gathering macOS Logon History using 'log show' and 'last' commands...")
            # Fixed SyntaxWarning by using a raw string for the command
            log_output = self.run_command(r"log show --predicate 'process == \"loginwindow\"' --last 1d | grep '\[loginwindow\]'", check_shell=True)
            if log_output:
                html_content += "<tr><td colspan='3'><b>Recent LoginWindow Events:</b><pre>"
                html_content += log_output
                html_content += "</pre></td></tr>"
            
            last_output = self.run_command("last -F", check_shell=True) # -F for full time
            if last_output:
                html_content += "<tr><td colspan='3'><b>User Login/Logout History ('last' command):</b><pre>"
                html_content += last_output
                html_content += "</pre></td></tr>"
        
        html_content += """
            </table>
        </body>
        </html>
        """
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"Logon Report completed (conceptual). The Report is saved to: {report_path}")

    def antivirus_placeholder(self):
        self.log_output("\nRunning Antivirus Status Report (Placeholder)...")
        report_path = self.get_report_folder_path("AntivirusReport.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <html>
        <head>
            <title>Antivirus Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h1 {{ color: #333; }}
                h2 {{ color: #0066cc; }}
                .active {{ color: #009900; }}
                .inactive {{ color: #FF0000; }}
                pre {{ background-color: #f9f9f9; padding: 10px; border: 1px solid #ddd; white-space: pre-wrap; }}
            </style>
        </head>
        <body>
            <h1>Antivirus Report - {self.suspect_computer_name}</h1>
            <h2>Date and Time: {current_time}</h2>
        """
        if sys.platform == "win32":
            self.log_output("Gathering Windows Antivirus status and exclusions (Microsoft Defender/SecurityCenter2)...")
            html_content += "<p>Windows: This requires querying Windows Defender via PowerShell (`Get-MpComputerStatus`, `Get-MpPreference`) or WMI (`root\\SecurityCenter2\\AntiVirusProduct`).</p>"
            html_content += "<p>Example PowerShell commands:</p><pre>"
            html_content += "Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled, FullScanProgress, QuickScanProgress, AMEngineVersion, AMProductVersion, AntivirusSignatureVersion, AntispywareSignatureVersion\n"
            html_content += "Get-MpPreference | Select-Object ExclusionPath, ExclusionExtension, ExclusionProcess, ExclusionIpAddress\n"
            html_content += "Get-WmiObject -Namespace \"root\\SecurityCenter2\" -Query \"SELECT * FROM AntiVirusProduct\"\n"
            html_content += "</pre>"
        elif sys.platform == "darwin":
            self.log_output("Gathering macOS Antivirus status (checking common paths/processes)...")
            av_paths = [
                "/Applications/Sophos Anti-Virus.app",
                "/Applications/CrowdStrike/Falcon.app",
                "/Library/Application Support/Malwarebytes/Malwarebytes Endpoint Agent",
            ]
            found_av = False
            for path in av_paths:
                if os.path.exists(path):
                    html_content += f"<p>Found potential AV: {path} (Status: Likely Installed)</p>"
                    found_av = True
            if not found_av:
                html_content += "<p class='inactive'>No common Antivirus installations detected via known paths. Manual verification may be required.</p>"
            
            # Check running processes for AV names
            processes_output = self.run_command("ps aux", check_shell=True)
            if processes_output:
                av_keywords = ["sophos", "crowdstrike", "malwarebytes", "eset", "avast"]
                html_content += "<h3>AV-related processes found:</h3><pre>"
                found_process_av = False
                for line in processes_output.strip().split('\n'):
                    for keyword in av_keywords:
                        if keyword in line.lower():
                            html_content += line + "\n"
                            found_process_av = True
                            break
                if not found_process_av:
                    html_content += "No AV-related processes identified by keywords."
                html_content += "</pre>"

        html_content += """
        </body>
        </html>
        """
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"Antivirus Report completed (conceptual). The Report is saved to: {report_path}")

    def web_history_placeholder(self):
        self.log_output("\nCopying Browser History Database files (Placeholder)...")
        self.log_output("This function requires identifying browser profile paths (which vary by OS and browser) and copying their SQLite database files (e.g., 'History', 'places.sqlite').")
        self.log_output("These files are often locked while the browser is running, requiring special handling or a forensic image. Parsing requires Python's 'sqlite3' module.")
        self.log_output("For remote machines, you'd need SSH (macOS) or SMB/WinRM (Windows) to copy these files.")
        
        report_path = self.get_report_folder_path("BrowserHistory_Notes.txt")
        with open(report_path, "w") as f:
            f.write("Notes on Browser History Collection:\n")
            f.write("This process involves locating browser profile directories (which are OS- and browser-specific),\n")
            f.write("copying their 'History' (Chrome/Edge/Brave) or 'places.sqlite' (Firefox) SQLite database files.\n")
            f.write("These files are typically locked by the browser if it's running, making live collection difficult.\n")
            f.write("Parsing the SQLite databases requires Python's 'sqlite3' module.\n")
            f.write("For remote collection, secure file transfer protocols like SCP/SFTP (over SSH) or SMB shares (Windows) would be necessary.\n")
        self.log_output(f"Browser History Collection notes saved to: {report_path}")

    def scheduled_tasks_placeholder(self):
        self.log_output("\nGenerating Scheduled Task Report (Placeholder)...")
        report_path = self.get_report_folder_path("ScheduledTasksReport.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <html>
        <head>
            <title>Scheduled Tasks Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Scheduled Tasks Report on {self.suspect_computer_name}</h1>
            <p>Report generated on: {current_time}</p>
        """
        if sys.platform == "win32":
            self.log_output("Gathering Windows Scheduled Tasks...")
            html_content += "<p>Windows: This requires querying the Task Scheduler. You'd typically use `powershell.exe -Command \"Get-ScheduledTask | Select-Object TaskName, State, LastRunTime, NextRunTime, Actions | ConvertTo-Json\"`.</p>"
        elif sys.platform == "darwin":
            self.log_output("Gathering macOS LaunchAgents/LaunchDaemons and Cron jobs...")
            launchctl_output = self.run_command("sudo launchctl list", check_shell=True)
            html_content += "<h2>LaunchAgents/LaunchDaemons (via `launchctl list`):</h2><pre>"
            if launchctl_output: html_content += launchctl_output
            html_content += "</pre>"

            cron_output = self.run_command("crontab -l", check_shell=True)
            html_content += "<h2>User Cron Jobs (via `crontab -l`):</h2><pre>"
            if cron_output: html_content += cron_output
            html_content += "</pre>"
        
        html_content += """
            </body>
            </html>
        """
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"Scheduled Task Report completed (conceptual). The Report is saved to: {report_path}")

    def installed_software_placeholder(self):
        self.log_output("\nRunning Installed Software Report (Placeholder)...")
        report_path = self.get_report_folder_path("InstalledSoftwareReport.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <html>
        <head>
            <title>Installed Software Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Installed Software Report for {self.suspect_computer_name}</h1>
            <p>Report generated on: {current_time}</p>
            <table>
                <tr><th>Name</th><th>Version</th><th>Publisher</th><th>Install Date</th><th>Location/Path</th></tr>
        """
        if sys.platform == "win32":
            self.log_output("Gathering Windows Installed Software (Registry/WMI)...")
            html_content += "<p>Windows: Software information is primarily in the Registry (Uninstall keys) or via WMI (Win32_Product, though this is discouraged for inventory).</p>"
            html_content += "<p>You would typically run PowerShell commands like `Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*` and parse the output.</p>"
        elif sys.platform == "darwin":
            self.log_output("Gathering macOS Installed Software (system_profiler/Application directories/package managers)...")
            apps_output = self.run_command("system_profiler SPApplicationsDataType", check_shell=True)
            if apps_output:
                html_content += "<tr><td colspan='5'><b>Applications (via `system_profiler`):</b><pre>"
                html_content += apps_output
                html_content += "</pre></td></tr>"
            
            # Basic listing of /Applications
            app_dir_output = self.run_command("ls -F /Applications", check_shell=True)
            if app_dir_output:
                html_content += "<tr><td colspan='5'><b>Applications Directory:</b><pre>"
                html_content += app_dir_output
                html_content += "</pre></td></tr>"

        html_content += """
            </table>
        </body>
        </html>
        """
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"Installed Software Report completed (conceptual). The Report is saved to: {report_path}")

    def usb_device_placeholder(self):
        self.log_output("\nGetting USB Drive Report (Placeholder)...")
        report_path = self.get_report_folder_path("USB_Devices_Report.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <html>
        <head>
            <title>USB Device Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>USB Device Report on {self.suspect_computer_name}</h1>
            <p>Report generated on: {current_time}</p>
            <h2>Currently Connected USB Devices</h2>
            <table>
                <tr><th>Friendly Name</th><th>Description</th><th>Manufacturer</th><th>Instance ID</th><th>Status</th></tr>
        """
        if sys.platform == "win32":
            self.log_output("Gathering Windows USB Device information (PnPDevice/WMI/Registry)...")
            html_content += "<p>Windows: USB device info is found using `Get-PnpDevice`, `Get-WmiObject Win32_PnPEntity`, and by inspecting registry keys (e.g., `HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\USB`).</p>"
            html_content += "<p>A complex PowerShell command or direct WMI/registry access via Python would be needed.</p>"
        elif sys.platform == "darwin":
            self.log_output("Gathering macOS USB Device information (system_profiler)...")
            usb_output = self.run_command("system_profiler SPUSBDataType", check_shell=True)
            if usb_output:
                html_content += "<tr><td colspan='5'><pre>"
                html_content += usb_output
                html_content += "</pre></td></tr>"
            else:
                html_content += "<tr><td colspan='5'>Could not retrieve macOS USB device information.</td></tr>"

        html_content += """
            </table>
            <h2>Previously Connected USB Devices (Conceptual)</h2>
            <p>For Windows, this involves parsing registry exports or SetupAPI logs. For macOS, it's primarily from system logs.</p>
        </body>
        </html>
        """
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"USB Device Report completed (conceptual). The Report is saved to: {report_path}")

    def event_viewer_placeholder(self):
        self.log_output("\nPreparing to copy Event Viewer Files (Placeholder)...")
        report_path = self.get_report_folder_path("EventViewer_Notes.txt")
        
        with open(report_path, "w") as f:
            f.write("Notes on Event Viewer Log Collection:\n")
            if sys.platform == "win32":
                f.write("Windows: Event Viewer logs are .evtx files typically located at C:\\Windows\\System32\\Winevt\\Logs\\.\n")
                f.write("Copying these live can be tricky; a PowerShell 'Copy-Item' with UNC path or a Python 'shutil.copyfile' (requiring appropriate permissions/remote access) could be used.\n")
                f.write("Parsing .evtx files in Python requires specialized libraries (e.g., 'python-evtx').\n")
            elif sys.platform == "darwin":
                f.write("macOS: There is no direct 'Event Viewer' equivalent. macOS uses a unified logging system.\n")
                f.write("Logs can be viewed and filtered using the `log show` command. Example: `log show --predicate 'process == \"loginwindow\"' --info`.\n")
                f.write("Specific log files are also in /var/log/ (e.g., system.log, install.log). Copying these requires permissions.\n")
            f.write("For remote collection, SSH (macOS) or SMB/WinRM (Windows) would be necessary.\n")
        self.log_output(f"Event Viewer/System Log Collection notes saved to: {report_path}")

    def browserext_placeholder(self):
        self.log_output("\nRunning Browser Extension identifier tool (Placeholder)...")
        self.log_output("This involves locating browser extension directories for each user profile (paths vary by OS/browser) and reading their 'manifest.json' files, and parsing with Python's 'json' module.")
        self.log_output("Example paths: Chrome/Edge/Brave extensions are in `AppData\\Local\\Google\\Chrome\\User Data\\Default\\Extensions` (Windows) or `~/Library/Application Support/Google/Chrome/Default/Extensions` (macOS).")
        self.log_output("For remote machines, secure file transfer is needed.")
        
        report_path = self.get_report_folder_path("BrowserExtensions_Notes.txt")
        with open(report_path, "w") as f:
            f.write("Notes on Browser Extension Collection:\n")
            f.write("This process requires locating each browser's extension directory for every user profile.\n")
            f.write("Paths are OS- and browser-specific.\n")
            f.write("For Chrome/Edge/Brave, extensions are usually within `.../User Data/Default/Extensions/` where each extension has its own folder with a `manifest.json` file.\n")
            f.write("The `manifest.json` file contains the extension's name, version, and description.\n")
            f.write("Parsing `manifest.json` requires Python's 'json' module.\n")
            f.write("Remote collection requires secure file transfer protocols like SCP/SFTP (over SSH) or SMB shares (Windows).\n")
        self.log_output(f"Browser Extension Collection notes saved to: {report_path}")

    def user_downloads_placeholder(self):
        self.log_output("\nCopying USER Downloads to local Desktop (Placeholder)...")
        self.log_output("This involves locating each user's 'Downloads' folder (e.g., `C:\\Users\\<user>\\Downloads` on Windows, `~/Downloads` on macOS), and then copying relevant files.")
        self.log_output("For remote machines, secure file transfer protocols like SCP/SFTP (over SSH) or SMB shares (Windows) are needed. It can transfer large amounts of data.")
        
        report_path = self.get_report_folder_path("UserDownloads_Notes.txt")
        with open(report_path, "w") as f:
            f.write("Notes on User Downloads Collection:\n")
            f.write("This function identifies the 'Downloads' folder for each user on the target machine.\n")
            f.write("It then copies the files to the local machine and generates a report (e.g., HTML) listing file names, sizes, and last modified dates.\n")
            f.write("Due to potentially large file sizes and number of files, this operation can take considerable time and disk space.\n")
            f.write("Remote collection requires secure file transfer protocols like SCP/SFTP (over SSH) or SMB shares (Windows).\n")
        self.log_output(f"User Downloads Collection notes saved to: {report_path}")

    def browser_artifacts_placeholder(self):
        self.log_output("\nRunning Browser Artifact Report (Placeholder)...")
        self.log_output("This is similar to web history/extensions but includes bookmarks, cookies, cache, etc. These are often in SQLite databases or JSON files.")
        self.log_output("Paths are OS/browser/user-profile specific. Parsing requires 'sqlite3' and 'json' modules.")
        self.log_output("Remote collection requires secure file transfer.")
        
        report_path = self.get_report_folder_path("BrowserArtifacts_Notes.txt")
        with open(report_path, "w") as f:
            f.write("Notes on Browser Artifacts Collection:\n")
            f.write("This comprehensive report includes various browser artifacts like bookmarks, cookies, cache, local storage, autofill data, etc.\n")
            f.write("Many of these are stored in SQLite databases (e.g., 'Cookies', 'Login Data', 'Web Data') or JSON files.\n")
            f.write("Location of these files is highly dependent on the OS, browser, and specific user profile.\n")
            f.write("Parsing involves using Python's 'sqlite3' and 'json' modules.\n")
            f.write("Remote collection requires secure file transfer protocols (e.g., SCP/SFTP over SSH) or SMB shares (Windows).\n")
            f.write("Files might be locked if the browser is running.\n")
        self.log_output(f"Browser Artifacts Collection notes saved to: {report_path}")

    def remove_pin_placeholder(self):
        self.log_output("\nRemoving Windows Pin/Biometrics (Placeholder) - This is a highly Windows-specific function.")
        self.log_output("This function directly manipulates Windows system files and services related to PIN and Biometric authentication (e.g., NGC folder, WinBioDatabase service).")
        self.log_output("A direct Python equivalent for macOS does not exist. macOS uses different mechanisms for Touch ID, Face ID, and local account passwords.")
        self.log_output("Attempting to implement this for macOS would require in-depth knowledge of macOS security frameworks and potentially undocumented APIs, which is not feasible.")
        self.log_output("For remote Windows, it would require WinRM/PowerShell Remoting with administrative privileges.")
        messagebox.showwarning("Function Not Applicable to macOS", "The 'Remove Windows Pin/Biometrics' function is highly specific to Windows operating systems and cannot be directly translated or implemented for macOS.")

    def remote_c_placeholder(self):
        self.log_output("\nAccessing Remote C: (Placeholder) - This is a Windows-specific SMB share access.")
        self.log_output("The 'C$' share is an administrative share common on Windows systems.")
        self.log_output("For macOS, accessing a remote share would typically involve mounting an SMB share (e.g., `smb://<computer_name>/C$`) which is handled by the OS, not directly within Python in the same way.")
        self.log_output("Python libraries like 'smbprotocol' could be used for programmatic SMB access, but it's not a direct equivalent to 'Invoke-Item -Path \\\\$remoteServer\\c$'.")
        messagebox.showwarning("Function Not Directly Applicable to macOS", "Accessing a remote C$ share is a Windows-specific operation. For macOS, you would typically use `Finder > Go > Connect to Server...` and enter `smb://<IP_or_Hostname>/C$`.")

    def shutdown_pc_placeholder(self):
        self.log_output("\nShutting Down PC (Placeholder)...")
        self.log_output("For Windows, this typically uses `Stop-Computer` (PowerShell) or `shutdown /s` (CMD).")
        self.log_output("For macOS, the equivalent local command is `sudo shutdown -h now` or `sudo /sbin/reboot`.")
        self.log_output("Remote execution for both OSes would usually involve SSH (e.g., using 'paramiko' in Python to send the command) and proper authentication/permissions.")
        self.log_output("This is a critical operation; user confirmation and robust error handling are essential.")
        
        if messagebox.askyesno("Confirm Shutdown", f"Are you sure you want to shut down {self.suspect_computer_name}? This action is irreversible remotely and will kill connections.", icon='warning'):
            self.log_output(f"Attempting to shut down {self.suspect_computer_name}...")
            try:
                if sys.platform == "win32":
                    # For local execution or via WinRM/SSH if configured
                    self.run_command(f"shutdown /s /f /t 0 /m \\\\{self.suspect_computer_name}", check_shell=True)
                elif sys.platform == "darwin":
                    # For local execution, requires sudo. For remote, SSH is needed.
                    self.run_command(f"sudo shutdown -h now", check_shell=True)
                self.log_output("Shutdown command sent. Verify machine status manually.")
            except Exception as e:
                self.log_output(f"Error attempting to shut down: {e}")
        else:
            self.log_output("Shutdown cancelled by user.")

    def disable_network_placeholder(self):
        self.log_output("\nDisabling Network Adapters (Placeholder)...")
        self.log_output("For Windows, this uses `Disable-NetAdapter` (PowerShell) or `netsh interface set interface name=\"Ethernet\" admin=disable` (CMD).")
        self.log_output("For macOS, the equivalent is `networksetup -setairportpower en0 off` (for Wi-Fi) or `networksetup -setnetworkserviceenabled \"<service_name>\" off`.")
        self.log_output("This is a critical operation as it will sever network connectivity. Remote execution would require SSH/WinRM.")
        
        if messagebox.askyesno("Confirm Disable Network", f"WARNING: This will disable network adapters on {self.suspect_computer_name}. You WILL lose connection.", icon='warning'):
            self.log_output(f"Attempting to disable network adapters on {self.suspect_computer_name}...")
            try:
                if sys.platform == "win32":
                    # For local execution or via WinRM/SSH if configured
                    self.run_command(f"powershell.exe -Command \"Get-NetAdapter | Disable-NetAdapter -Confirm:$false\"", check_shell=True)
                elif sys.platform == "darwin":
                    # For local execution, requires sudo. For remote, SSH is needed.
                    # This will disable Wi-Fi (en0) and Ethernet (if present). Requires adapting to actual interface names.
                    self.run_command(f"sudo networksetup -setairportpower en0 off", check_shell=True)
                    self.run_command(f"sudo networksetup -setnetworkserviceenabled \"Ethernet\" off", check_shell=True) # Common name
                self.log_output("Network disable command sent. Verify machine status manually.")
            except Exception as e:
                self.log_output(f"Error attempting to disable network: {e}")
        else:
            self.log_output("Network disable cancelled by user.")

    def computer_accounts_placeholder(self):
        self.log_output("\nOpening Computer Account Tool (Placeholder)...")
        self.log_output("This PowerShell function reads a list of computer names from a file and checks if a specific user's profile folder exists on each. This implies checking remote file shares or using remote execution.")
        self.log_output("For remote Windows, this would involve checking SMB shares (`\\\\<computer>\\C$\\Users\\<username>`).")
        self.log_output("For remote macOS, this would require SSH and then listing directories (e.g., `ls /Users/<username>`).")
        self.log_output("The 'Test-ComputerOnline' part means performing a ping check, which is already in `main_ping`.")
        
        report_path = self.get_report_folder_path("ComputerAccounts_Notes.txt")
        with open(report_path, "w") as f:
            f.write("Notes on Computer Accounts Check:\n")
            f.write("This function aims to identify on which computers a specific user has a profile folder (implying they logged in).\n")
            f.write("It requires a list of target computer names.\n")
            f.write("For Windows targets, you would attempt to access `\\\\<computer>\\C$\\Users\\<username>` via SMB/UNC paths.\n")
            f.write("For macOS targets, you would use SSH (e.g., 'paramiko') to execute `ls /Users/<username>` remotely.\n")
            f.write("Permissions are critical for accessing remote user directories.\n")
        self.log_output(f"Computer Accounts check notes saved to: {report_path}")

    def image_thumbnails_placeholder(self):
        self.log_output("\nGenerating User Image Reports (Placeholder)...")
        self.log_output("This involves locating user image directories (`Pictures`, `Downloads`, `Recycle Bin`) and generating thumbnails (or base64 encoding images directly into HTML) for a report.")
        self.log_output("Paths vary by OS. For `Recycle Bin`, Windows has specific structure (`$Recycle.Bin`), macOS has `~/.Trash` or `.Trashes`.")
        self.log_output("Copying image files from remote machines requires secure file transfer.")
        
        report_path = self.get_report_folder_path("ImageThumbnails_Notes.txt")
        with open(report_path, "w") as f:
            f.write("Notes on Image Thumbnails Report:\n")
            f.write("This function searches for image files in standard user directories (Pictures, Downloads, Recycle Bin).\n")
            f.write("It then typically generates an HTML report with embedded (base64 encoded) thumbnails of these images.\n")
            f.write("Image file paths and Recycle Bin structures vary significantly between Windows and macOS.\n")
            f.write("Copying these files from remote machines (which can be very large) requires secure file transfer protocols (e.g., SCP/SFTP over SSH) or SMB shares (Windows).\n")
            f.write("Python libraries like `PIL (Pillow)` can be used for image processing (thumbnailing/resizing).\n")
        self.log_output(f"Image Thumbnails Report notes saved to: {report_path}")

    def startup_placeholder(self):
        self.log_output("\nRunning Startup Report (Placeholder)...")
        report_path = self.get_report_folder_path("StartupItemsReport.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <html>
        <head>
            <title>Startup Items Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Startup Items on {self.suspect_computer_name}</h1>
            <p>Report generated on: {current_time}</p>
        """
        if sys.platform == "win32":
            self.log_output("Gathering Windows Startup Items (Win32_StartupCommand/Registry)...")
            html_content += "<p>Windows: Startup items are typically found via `Get-CimInstance -Query \"SELECT * FROM Win32_StartupCommand\"` or by inspecting Registry 'Run' keys (`HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run`).</p>"
        elif sys.platform == "darwin":
            self.log_output("Gathering macOS Startup Items (LaunchAgents/LaunchDaemons/Login Items/Cron)...")
            launch_output = self.run_command("sudo launchctl list", check_shell=True)
            html_content += "<tr><td colspan='3'><b>LaunchAgents/LaunchDaemons (via `launchctl list`):</b><pre>"
            if launch_output: html_content += launch_output
            html_content += "</pre></td></tr>"
            
            # Login Items (GUI-managed items that launch when user logs in)
            html_content += "<tr><td colspan='3'><b>User Login Items (conceptual, requires parsing plists/AppleScript):</b><br/>"
            html_content += "For local user: `defaults read ~/Library/Preferences/com.apple.loginitems.plist` (or other relevant plists). Parsing can be tricky.</td></tr>"

        html_content += """
            </body>
            </html>
        """
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"Startup Report completed (conceptual). The Report is saved to: {report_path}")

    def wifi_network_placeholder(self):
        self.log_output("\nRunning WIFI and Network Report (Placeholder)...")
        report_path = self.get_report_folder_path("NetworkAdapterReport.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <html>
        <head>
            <title>WIFI and Network Adapter Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>WIFI and Network Adapter Report - {self.suspect_computer_name}</h1>
            <p>Report generated on: {current_time}</p>
            <h2>Network Adapters</h2>
            <table>
                <tr><th>Adapter Name</th><th>MAC Address</th><th>IP Addresses</th><th>Status</th></tr>
        """
        if sys.platform == "win32":
            self.log_output("Gathering Windows Network Adapter info ('Get-NetAdapter'/'ipconfig')...")
            html_content += "<p>Windows: Network adapter info is obtained via `powershell.exe -Command \"Get-NetAdapter | Select-Object Name, MacAddress, Status\"` and `ipconfig /all`.</p>"
            html_content += "<p>For Wi-Fi profiles/passwords, `netsh wlan show profiles key=clear` is used, but extracting passwords from remote machines requires admin rights and parsing.</p>"
        elif sys.platform == "darwin":
            self.log_output("Gathering macOS Network Adapter info ('networksetup'/'ifconfig')...")
            html_content += "<tr><td colspan='4'><b>Hardware Ports (via `networksetup -listallhardwareports`):</b><pre>"
            hardware_ports = self.run_command("networksetup -listallhardwareports", check_shell=True)
            if hardware_ports: html_content += hardware_ports
            html_content += "</pre></td></tr>"
            
            html_content += "<tr><td colspan='4'><b>Network Interface Configuration (via `ifconfig`):</b><pre>"
            ifconfig_output = self.run_command("ifconfig", check_shell=True)
            if ifconfig_output: html_content += ifconfig_output
            html_content += "</pre></td></tr>"
            
            html_content += "<tr><td colspan='4'><b>Wi-Fi Network Passwords (conceptual, requires sudo/keychain access):</b><br/>"
            html_content += "On macOS, Wi-Fi passwords are in the Keychain. Retrieving them programmatically requires elevated privileges and specific 'security' commands, e.g., `sudo security find-generic-password -ga \"<SSID>\"` and parsing.<br/>"
            html_content += "This cannot be done directly without user interaction or careful permission management."
            html_content += "</td></tr>"

        html_content += """
            </table>
        </body>
        </html>
        """
        with open(report_path, "w") as f:
            f.write(html_content)
        self.log_output(f"WIFI and Network Report completed (conceptual). The Report is saved to: {report_path}")

    def IRIS_file_report_placeholder(self):
        self.log_output("\nGenerating Printable Result (Placeholder)...")
        self.log_output("This function iterates through all files generated in the IRIS REPORTS folder for the suspect computer.")
        self.log_output("It compiles a list of these files, their creation/modification times, and sizes into a single HTML report for easy printing/review.")
        
        report_folder = os.path.join(os.path.expanduser("~"), "Desktop", f"{self.suspect_computer_name} IRIS REPORTS")
        output_file = os.path.join(report_folder, "Captured File Report.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        file_list_html = ""
        try:
            for root, _, files in os.walk(report_folder):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    stat = os.stat(file_path)
                    created_time = datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                    modified_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    size_kb = round(stat.st_size / 1024, 2)
                    
                    # Make path relative to the main report folder for cleaner display
                    display_path = os.path.relpath(file_path, report_folder)
                    file_list_html += f"<tr><td>{display_path}</td><td>{created_time}</td><td>{modified_time}</td><td>{size_kb} KB</td></tr>"
        except Exception as e:
            self.log_output(f"Error gathering file list for printable report: {e}")
            file_list_html = f"<tr><td colspan='4'>Error gathering file list: {e}</td></tr>"

        html_content = f"""
        <html>
        <head>
            <title>IRIS Captured File Report - {self.suspect_computer_name}</title>
            <style>
                body {{ font-family: Segoe UI, Arial, sans-serif; background-color: #f4f4f4; color: #333; }}
                h1, h2, h3 {{ text-align: center; color: #003366; }}
                table {{ width: 95%; margin: 20px auto; border-collapse: collapse; box-shadow: 0 0 8px rgba(0,0,0,0.1); page-break-inside: auto; }}
                th, td {{ border: 1px solid #ccc; padding: 10px; text-align: left; }}
                th {{ background-color: #003366; color: white; }}
                tr:nth-child(even) {{ background-color: #eaf0f6; }}
                tr:nth-child(odd) {{ background-color: #ffffff; }}
                td {{ font-size: 14px; }}
                tr.page-break {{ page-break-after: always; }}
            </style>
        </head>
        <body>
            <h1>IRIS Captured File Report</h1>
            <h2>Machine: {self.suspect_computer_name}</h2>
            <h3>Report Generated: {current_time}</h3>
            <table>
                <thead>
                    <tr><th>File Path</th><th>Date Created</th><th>Date Modified</th><th>Size</th></tr>
                </thead>
                <tbody>
                    {file_list_html}
                </tbody>
            </table>
        </body>
        </html>
        """
        with open(output_file, "w") as f:
            f.write(html_content)
        self.log_output(f"Printable Report generated: {output_file}")


root = tk.Tk()
app = IRISApp(root)
root.mainloop()