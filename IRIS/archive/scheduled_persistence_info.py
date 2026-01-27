import sys
import os
import re
import datetime
import json
from typing import Any

# Import necessary components from helpers.py
from helpers import MockAppInstance, MockHelpers

def generate_scheduled_persistence_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """
    Gathers and reports scheduled tasks, startup items, and checks for malicious scripts.
    """
    app_instance.log_output("\n--- Generating Scheduled & Persistence Report ---")
    
    html_body = "<h2>Scheduled Tasks Report</h2>"

    if sys.platform == "darwin":
        # --- LaunchDaemons (System-wide, often requires sudo) ---
        html_body += "<h3>macOS LaunchDaemons (System-wide Tasks)</h3>"
        app_instance.log_output("Gathering LaunchDaemons from /Library/LaunchDaemons/ and /System/Library/LaunchDaemons/...")
        daemon_paths = ["/Library/LaunchDaemons/", "/System/Library/LaunchDaemons/"] 
        
        daemon_data = []
        for path_dir in daemon_paths:
            app_instance.log_output(f"Checking LaunchDaemon directory: {path_dir}")
            if os.path.exists(path_dir):
                app_instance.log_output(f"Directory exists: {path_dir}")
                list_output = helpers.run_command(f"sudo ls {path_dir}", check_shell=True, app_instance=app_instance) 
                if list_output:
                    app_instance.log_output(f"Successfully listed files in {path_dir}. Processing {len(list_output.strip().splitlines())} files.")
                    for filename in list_output.strip().splitlines(): 
                        if filename.endswith(".plist"):
                            plist_file_path = os.path.join(path_dir, filename)
                            app_instance.log_output(f"  Attempting to read plist: {plist_file_path}")
                            data = helpers.read_plist_file(plist_file_path, app_instance=app_instance)
                            if data:
                                program_arg = "N/A"
                                if "Program" in data:
                                    program_arg = data["Program"]
                                elif "ProgramArguments" in data:
                                    program_arg = " ".join(map(str, data["ProgramArguments"]))
                                
                                daemon_data.append({
                                    "Source": plist_file_path,
                                    "Label": data.get("Label", "N/A"),
                                    "Program": program_arg,
                                    "RunAtLoad": data.get("RunAtLoad", False),
                                    "StartInterval": data.get("StartInterval", "N/A"),
                                    "StartCalendarInterval": data.get("StartCalendarInterval", "N/A"),
                                    "KeepAlive": data.get("KeepAlive", False)
                                })
                                app_instance.log_output(f"  ✅ Successfully processed {plist_file_path}.")
                            else:
                                app_instance.log_output(f"  ❌ Could not read content of {plist_file_path} (Permission denied or invalid format).")
                        else:
                            app_instance.log_output(f"  Skipping non-plist file: {filename}")
                else:
                    app_instance.log_output(f"❌ Could not list LaunchDaemons in {path_dir} (Command failed or permission denied for `sudo ls`).")
            else:
                app_instance.log_output(f"❌ Directory does not exist (LaunchDaemons): {path_dir}")
        
        if daemon_data:
            html_body += "<table><tr><th>Source</th><th>Label</th><th>Program/Command</th><th>Run At Load</th><th>Interval (sec)</th><th>Calendar Interval</th><th>Keep Alive</th></tr>"
            for item in daemon_data:
                html_body += f"<tr><td>{item['Source']}</td><td>{item['Label']}</td><td><pre>{item['Program']}</pre></td><td>{item['RunAtLoad']}</td><td>{item['StartInterval']}</td><td>{item['StartCalendarInterval']}</td><td>{item['KeepAlive']}</td></tr>"
            html_body += "</table>"
        else:
            html_body += "<p>No LaunchDaemons found or processed. Some may require elevated privileges to list or read contents.</p>"


        # --- LaunchAgents (User-specific and System-wide for all users) ---
        html_body += "<h3>macOS LaunchAgents (User-Specific and All-User Tasks)</h3>"
        app_instance.log_output("Gathering LaunchAgents from ~/Library/LaunchAgents/ and /Library/LaunchAgents/...")
        agent_paths = [os.path.expanduser("~/Library/LaunchAgents/"), "/Library/LaunchAgents/"]
        
        agent_data = []
        for path_dir in agent_paths:
            app_instance.log_output(f"Checking LaunchAgent directory: {path_dir}")
            if os.path.exists(path_dir):
                app_instance.log_output(f"Directory exists: {path_dir}")
                command_to_list = f"sudo ls {path_dir}" if path_dir == "/Library/LaunchAgents/" else f"ls {path_dir}"
                list_output = helpers.run_command(command_to_list, check_shell=True, app_instance=app_instance) 
                if list_output:
                    app_instance.log_output(f"Successfully listed files in {path_dir}. Processing {len(list_output.strip().splitlines())} files.")
                    for filename in list_output.strip().splitlines():
                        if filename.endswith(".plist"):
                            plist_file_path = os.path.join(path_dir, filename)
                            app_instance.log_output(f"  Attempting to read plist: {plist_file_path}")
                            data = helpers.read_plist_file(plist_file_path, app_instance=app_instance)
                            if data:
                                program_arg = "N/A"
                                if "Program" in data:
                                    program_arg = data["Program"]
                                elif "ProgramArguments" in data:
                                    program_arg = " ".join(map(str, data["ProgramArguments"]))
                                
                                agent_data.append({
                                    "Source": plist_file_path,
                                    "Label": data.get("Label", "N/A"),
                                    "Program": program_arg,
                                    "RunAtLoad": data.get("RunAtLoad", False),
                                    "StartInterval": data.get("StartInterval", "N/A"),
                                    "StartCalendarInterval": data.get("StartCalendarInterval", "N/A"),
                                    "KeepAlive": data.get("KeepAlive", False)
                                })
                                app_instance.log_output(f"  ✅ Successfully processed {plist_file_path}.")
                            else:
                                app_instance.log_output(f"  ❌ Could not read content of {plist_file_path} (Permission denied or invalid format).")
                        else:
                            app_instance.log_output(f"  Skipping non-plist file: {filename}")
                else:
                    app_instance.log_output(f"❌ Could not list LaunchAgents in {path_dir} (Command failed or permission denied for `{command_to_list}`).")
            else:
                app_instance.log_output(f"❌ Directory does not exist (LaunchAgents): {path_dir}")

        if agent_data:
            html_body += "<table><tr><th>Source</th><th>Label</th><th>Program/Command</th><th>Run At Load</th><th>Interval (sec)</th><th>Calendar Interval</th><th>Keep Alive</th></tr>"
            for item in agent_data:
                html_body += f"<tr><td>{item['Source']}</td><td>{item['Label']}</td><td><pre>{item['Program']}</pre></td><td>{item['RunAtLoad']}</td><td>{item['StartInterval']}</td><td>{item['StartCalendarInterval']}</td><td>{item['KeepAlive']}</td></tr>"
            html_body += "</table>"
        else:
            html_body += "<p>No LaunchAgents found or processed.</p>"

        # --- Cron Jobs (Traditional Unix Scheduling) ---
        html_body += "<h3>macOS Cron Jobs</h3>"
        app_instance.log_output("Gathering current user cron jobs via `crontab -l`...")
        cron_output = helpers.run_command("crontab -l", check_shell=True, app_instance=app_instance) 
        if cron_output:
            html_body += "<h4>Current User Crontab:</h4>"
            html_body += f"<pre>{cron_output}</pre>"
        else:
            app_instance.log_output("No cron jobs found for current user or `crontab -l` command failed to retrieve output.")
            html_body += "<p>No cron jobs found for current user.</p>" 

        # System-wide cron directories (often contain scripts, not direct cron entries)
        html_body += "<h4>System-wide Cron Directories and Files:</h4>"
        cron_system_paths = ["/etc/crontab", "/etc/cron.d/", "/etc/cron.daily/", "/etc/cron.hourly/", "/etc/cron.monthly/", "/etc/cron.weekly/"]
        found_system_cron_info = False
        for cpath in cron_system_paths:
            app_instance.log_output(f"Checking system cron directory/file: {cpath}")
            if os.path.exists(cpath):
                app_instance.log_output(f"Directory exists: {cpath}")
                if os.path.isdir(cpath):
                    scripts_in_dir = helpers.run_command(f"sudo ls -l {cpath}", check_shell=True, app_instance=app_instance) 
                    if scripts_in_dir:
                        app_instance.log_output(f"Successfully listed scripts in {cpath}.")
                        html_body += f"<h5>Contents of directory: {cpath}</h5><pre>{scripts_in_dir}</pre>" 
                        found_system_cron_info = True
                    else:
                        app_instance.log_output(f"❌ Could not list contents of directory {cpath} (Command failed or permission denied for `sudo ls -l`).")
                elif os.path.isfile(cpath):
                    file_content = helpers.run_command(f"sudo cat {cpath}", check_shell=True, app_instance=app_instance) 
                    if file_content:
                        app_instance.log_output(f"Successfully read content of {cpath}.")
                        html_body += f"<h5>Content of file: {cpath}</h5><pre>{file_content}</pre>" 
                        found_system_cron_info = True
                    else:
                        app_instance.log_output(f"❌ Could not read content of {cpath} (Command failed or permission denied for `sudo cat`).")
            else:
                app_instance.log_output(f"❌ Cron directory/file does not exist: {cpath}")
        if not found_system_cron_info:
            html_body += "<p>No system-wide cron scripts or crontab files found in standard locations or permission denied.</p>"
            app_instance.log_output("No system-wide cron information found or accessible.")

    else:
        html_body += "<p>Scheduled tasks reporting for Windows/Linux is different and not yet fully implemented here. (Only basic macOS scaffolding).</p>"

    # --- Startup Items (Placeholder) ---
    html_body += "<h2>Startup Items</h2>"
    html_body += "<p>Startup item reporting is not yet implemented. This would involve checking various locations like user login items, system-wide startup scripts, and service configurations.</p>"

    # --- Script Check (Malicious Scripts) ---
    html_body += "<h2>Potentially Malicious Running Scripts</h2>"
    html_body += """
<p>This report identifies potentially malicious scripts running on the system by checking for suspicious keywords in process command lines.</p>
<table><tr><th>PID</th><th>User</th><th>Command Line</th></tr>
"""

    if sys.platform == "win32":
        app_instance.log_output("Scanning for suspicious PowerShell processes on Windows...")
        script_check_results = helpers.run_command(
            r"powershell.exe -Command \"Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match 'http|https|base64|powershell -e|pwsh -e' } | Select-Object ProcessId, Name, CommandLine | ConvertTo-Json\"", 
            check_shell=True, app_instance=app_instance
        )
        if script_check_results:
            try:
                processes = json.loads(script_check_results)
                for proc in processes:
                    html_body += f"<tr><td>{proc.get('ProcessId', 'N/A')}</td><td>{proc.get('Name', 'N/A')}</td><td>{proc.get('CommandLine', 'N/A')}</td></tr>"
                html_body += "</table>"
            except json.JSONDecodeError:
                app_instance.log_output("Error parsing PowerShell output for malicious script check.")
                html_body += "<tr><td colspan='3' style='color: red;'>Error parsing suspicious script check results.</td></tr></table>"
        else:
            html_body += "<tr><td colspan='3' style='color: green; font-weight: bold;'>No suspicious PowerShell activity detected.</td></tr></table>"

    elif sys.platform == "darwin":
        app_instance.log_output("Scanning for suspicious processes on macOS using 'ps aux'...")
        suspicious_patterns = r"(curl|wget|python -c|perl -e|php -r).*?(http|https)|(base64 -D)"
        
        all_processes = helpers.run_command("ps aux", check_shell=True, app_instance=app_instance)
        if all_processes:
            found_suspicious = False
            for line in all_processes.strip().split('\n')[1:]:
                if re.search(suspicious_patterns, line, re.IGNORECASE):
                    parts = line.strip().split(None, 10)
                    if len(parts) >= 11:
                        pid = parts[1]
                        user = parts[0]
                        cmd = " ".join(parts[10:])
                        html_body += f"<tr><td>{pid}</td><td>{user}</td><td>{cmd}</td></tr>"
                        found_suspicious = True
            html_body += "</table>"
            
            if not found_suspicious:
                html_body = html_body.replace("</table>", "<tr><td colspan='3' style='color: green; font-weight: bold;'>No suspicious activity detected on macOS.</td></tr></table>")
        else:
            html_body += "<tr><td colspan='3'>Could not retrieve process list.</td></tr></table>"
    html_body += "<p>For more detailed interpretations or comparisons, specialized benchmarking tools are required.</p>"


    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Scheduled_Persistence_Report.html", 
        "Scheduled Tasks & Persistence Report", 
        html_body,
        browser_preference=browser_preference
    )

