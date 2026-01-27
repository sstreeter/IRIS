# IRIS (Incident Response & Investigation System) Incident Response Toolkit 
# GUI Application

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from datetime import datetime, timedelta
import socket
import os
import sys

# Ensure IRIS package is discoverable
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from IRIS.helpers import MockAppInstance, Helpers

# Report generation functions grouped for clarity
from IRIS.reports.system_info import system_hardware_info, usb_camera_bluetooth_report, images_report
from IRIS.reports.user_security import (
    antivirus_status_report, web_history_report, console_log_report,
    user_activity_report
)
from IRIS.reports.network import (
    tcp_connections_report, network_config_report, firewall_rules_report,
    ping_util_report, whois_report
)
from IRIS.reports.process_software import (
    running_processes_report, installed_software_report
)
from IRIS.reports.persistence_malware import (
    scheduled_tasks_report, startup_items_report,
    script_check_report, process_persistence_report
)

class IRISGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IRIS Incident Response Console")
        self.geometry("1280x720")
        self.resizable(False, False)
        self.suspect_hostname = socket.gethostname()

        self.app_instance = MockAppInstance()
        #self.helpers = Helpers(use_mock=True)
        self.helpers = Helpers(use_mock=False)
        self.app_instance.set_hostname(self.suspect_hostname)

        self._build_ui()

    def _build_ui(self):
        self._build_top_bar()
        self._build_left_panel()
        self._build_right_panel()
        self._build_bottom_tools()
        self._build_console()

    def _build_top_bar(self):
        top = tk.Frame(self, bd=2, relief=tk.GROOVE)
        top.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        tk.Label(top, text="Browse for Logs:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(5,5))
        self.browser_var = tk.StringVar(value="System Default")
        ttk.Combobox(top, textvariable=self.browser_var,
                     values=["System Default","Chrome","Firefox","Safari","Edge","Brave"],
                     width=12, state="readonly").pack(side=tk.LEFT)

        tk.Label(top, text="Time Range:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(10,5))
        self.time_range_var = tk.StringVar(value="All Time")
        tr_cb = ttk.Combobox(top, textvariable=self.time_range_var,
                     values=["Last Hour", "Last 24 Hours", "Last 7 Days", "All Time", "Custom Range"],
                     width=14, state="readonly")
        tr_cb.pack(side=tk.LEFT)
        tr_cb.bind("<<ComboboxSelected>>", self.on_time_range_change)

        tk.Label(top, text="Suspect:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(10,5))
        self.suspect_var = tk.StringVar(value=self.suspect_hostname)
        tk.Entry(top, textvariable=self.suspect_var, width=20).pack(side=tk.LEFT)
        tk.Button(top, text="Set", command=self.set_suspect_computer).pack(side=tk.LEFT, padx=5)

    def on_time_range_change(self, event=None):
        selection = self.time_range_var.get()
        now = datetime.now()
        start = None
        end = None # passing None often implies "Now" for end
        
        if selection == "Last Hour":
            start = now - timedelta(hours=1)
        elif selection == "Last 24 Hours":
            start = now - timedelta(hours=24)
        elif selection == "Last 7 Days":
            start = now - timedelta(days=7)
        elif selection == "All Time":
            start = None
            end = None
        elif selection == "Custom Range":
            # Prompt for Start
            s_str = simpledialog.askstring("Custom Start", "Start Time (YYYY-MM-DD HH:MM):", parent=self)
            if s_str:
                try:
                    start = datetime.strptime(s_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    self.log("❌ Invalid Start Date Format. Using 'All Time'.")
                    self.time_range_var.set("All Time")
                    return
                
                # Prompt for End
                e_str = simpledialog.askstring("Custom End", "End Time (YYYY-MM-DD HH:MM) [Leave empty for Now]:", parent=self)
                if e_str:
                    try:
                        end = datetime.strptime(e_str, "%Y-%m-%d %H:%M")
                    except ValueError:
                        self.log("❌ Invalid End Date Format. Using 'Now'.")
            else:
                self.log("⚠️ Custom Range Cancelled. Reverting to 'All Time'.")
                self.time_range_var.set("All Time")
                return

        # Update App Instance
        self.app_instance.time_range = {"start": start, "end": end}
        
        # Log feedback
        range_desc = "All Time"
        if start:
            s_fmt = start.strftime("%Y-%m-%d %H:%M")
            e_fmt = end.strftime("%Y-%m-%d %H:%M") if end else "Now"
            range_desc = f"{s_fmt} to {e_fmt}"
        
        self.log(f"⏰ Time Range Set: {selection} ({range_desc})")

    def _build_left_panel(self):
        left = tk.LabelFrame(self, text="Diagnostic Reports", padx=5, pady=5)
        left.place(x=10, y=70, width=200, height=580)

        self.report_map = [
            ("Run All Reports", self.run_all_reports),
            ("System Information", self.run_system_info),
            ("USB, Camera & Bluetooth", self.run_usb_camera_bluetooth_report),
            ("Local Accounts", self.run_local_accounts_report),
            ("Logon Report", self.run_logon_report),
            ("Antivirus Status", self.run_antivirus_status_report),
            ("Web History", self.run_web_history_report),
            ("TCP Connections", self.run_tcp_connections_report),
            ("Network Configuration", self.run_network_config_report),
            ("Firewall Rules", self.run_firewall_rules_report),
            ("Running Processes", self.run_running_processes_report),
            ("Installed Software", self.run_installed_software_report),
            ("Images Report", self.run_images_report),
            ("macOS Console Report", self.run_console_log_report),
            ("Scheduled Tasks", self.run_scheduled_tasks_report),
            ("Startup Items", self.run_startup_items_report),
            ("Script Check", self.run_script_check_report),
            ("Process Persistence", self.run_process_persistence_report),
        ]

        for label, cmd in self.report_map:
            tk.Button(left, text=label, width=24, anchor="w", command=cmd).pack(pady=2)

    def _build_right_panel(self):
        right = tk.LabelFrame(self, text="Browser & Host Actions", padx=5, pady=5)
        right.place(x=1070, y=70, width=200, height=580)

        actions = [
            "Chrome Extension", "User Downloads", "Browser Artifacts",
            "Computer Accounts Notes", "Disable Network", "Shutdown System", "Ping",
            "Scan URL", "Lookup Host", "Check IP Reputation"
        ]

        # Action command map
        self.host_action_map = {
            "Ping": self.run_ping_report,
            "User Downloads": self.run_user_activity_report,
            "Chrome Extension": self.run_user_activity_report,
            "Scan URL": lambda: self.open_browser_tool("https://www.virustotal.com/gui/home/upload"),
            "Lookup Host": lambda: self.open_browser_tool("https://ipinfo.io/"),
            "Check IP Reputation": lambda: self.open_browser_tool("https://www.talosintelligence.com/")
        }

        for label in actions:
            cmd = self.host_action_map.get(label, lambda l=label: self.log(f"⚠️ Host action '{l}' not implemented yet."))
            tk.Button(right, text=label, width=24, anchor="w", command=cmd).pack(pady=2)

    def _build_bottom_tools(self):
        bottom_frame = tk.LabelFrame(self, text="Investigation Tools & Other", padx=5, pady=5)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        row1 = tk.Frame(bottom_frame)
        row1.pack(side=tk.TOP, fill=tk.X, pady=2)
        row2 = tk.Frame(bottom_frame)
        row2.pack(side=tk.TOP, fill=tk.X, pady=2)

        tools_row1 = ["MAC Vendor", "URL Check", "WHOIS", "Console Report", "Images"]
        tools_row2 = ["DB Browser for SQLite Download", "SQL Query", "Printable Result"]

        # Tool command map
        self.tool_map = {
            "MAC Vendor": self.run_network_config_report,
            "WHOIS": self.run_whois_report,
            "Ping": self.run_ping_report,
            "Console Report": self.run_console_log_report,
            "Images": self.run_images_report,
            "URL Check": lambda: self.open_browser_tool("https://urlscan.io/"),
            "DB Browser for SQLite Download": lambda: self.open_browser_tool("https://sqlitebrowser.org/dl/")
        }

        for label in tools_row1:
            cmd = self.tool_map.get(label, lambda l=label: self.log(f"⚠️ Tool '{l}' not implemented yet."))
            tk.Button(row1, text=label, width=18, command=cmd).pack(side=tk.LEFT, padx=5)

        for label in tools_row2:
            cmd = self.tool_map.get(label, lambda l=label: self.log(f"⚠️ Tool '{l}' not implemented yet."))
            tk.Button(row2, text=label, width=28, command=cmd).pack(side=tk.LEFT, padx=5)

        tk.Button(bottom_frame, text="v3.2", width=8, command=self.show_version_info).place(relx=1.0, rely=1.0, x=-5, y=-5, anchor="se")

    def _build_console(self):
        console_frame = tk.LabelFrame(self, text="Console Output", padx=5, pady=5)
        console_frame.place(x=220, y=70, width=840, height=580)

        self.console = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, font=("Courier", 10))
        self.console.pack(fill=tk.BOTH, expand=True)
        self.log(f"Using auto‑detected/default Suspect Computer: {self.suspect_hostname}")

    def log(self, msg):
        self.console.insert(tk.END, msg + "\n")
        self.console.see(tk.END)

    def set_suspect_computer(self):
        name = self.suspect_var.get()
        self.suspect_hostname = name
        self.app_instance.set_hostname(name)
        self.log(f"✅ Suspect computer set to: {name}")

    def run_all_reports(self):
        self.log("▶ Running all reports...")
        pref = self.browser_var.get()
        for _, cmd in self.report_map[1:]:  # skip "Run All"
            cmd(pref)
        self.log("✅ All reports completed.")

    def _run_wrapper(self, func, label, browser_pref=None):
        self.log(f"▶ Running {label}...")
        try:
            func(self.app_instance, self.helpers, browser_pref)
            self.log(f"✅ {label} generated.")
        except Exception as e:
            self.log(f"❌ Error in {label}: {e}")

    # Individual report methods mapped to wrappers
    def run_system_info(self, browser_pref=None):
        return self._run_wrapper(system_hardware_info.generate_system_hardware_report,
                                 "System Information Report", browser_pref)

    def run_usb_camera_bluetooth_report(self, browser_pref=None):
        return self._run_wrapper(usb_camera_bluetooth_report.generate_usb_camera_bluetooth_report,
                                 "USB/Camera/Bluetooth Report", browser_pref)

    def run_local_accounts_report(self, browser_pref=None):
        return self._run_wrapper(local_accounts_report.generate_local_accounts_report,
                                 "Local Accounts Report", browser_pref)

    def run_logon_report(self, browser_pref=None):
        return self._run_wrapper(logon_report.generate_logon_report,
                                 "Logon Report", browser_pref)

    def run_antivirus_status_report(self, browser_pref=None):
        return self._run_wrapper(antivirus_status_report.generate_antivirus_status_report,
                                 "Antivirus Status Report", browser_pref)

    def run_web_history_report(self, browser_pref=None):
        return self._run_wrapper(web_history_report.generate_web_history_report,
                                 "Web History Report", browser_pref)

    def run_tcp_connections_report(self, browser_pref=None):
        return self._run_wrapper(tcp_connections_report.generate_tcp_connections_report,
                                 "TCP Connections Report", browser_pref)

    def run_network_config_report(self, browser_pref=None):
        return self._run_wrapper(network_config_report.generate_network_config_report,
                                 "Network Configuration Report", browser_pref)

    def run_firewall_rules_report(self, browser_pref=None):
        return self._run_wrapper(firewall_rules_report.generate_firewall_rules_report,
                                 "Firewall Rules Report", browser_pref)

    def run_running_processes_report(self, browser_pref=None):
        return self._run_wrapper(running_processes_report.generate_running_processes_report,
                                 "Running Processes Report", browser_pref)

    def run_installed_software_report(self, browser_pref=None):
        return self._run_wrapper(installed_software_report.generate_installed_software_report,
                                 "Installed Software Report", browser_pref)

    def run_scheduled_tasks_report(self, browser_pref=None):
        return self._run_wrapper(scheduled_tasks_report.generate_scheduled_tasks_report,
                                 "Scheduled Tasks Report", browser_pref)

    def run_startup_items_report(self, browser_pref=None):
        return self._run_wrapper(startup_items_report.generate_startup_items_report,
                                 "Startup Items Report", browser_pref)

    def run_script_check_report(self, browser_pref=None):
        return self._run_wrapper(script_check_report.generate_script_check_report,
                                 "Script Check Report", browser_pref)

    def run_process_persistence_report(self, browser_pref=None):
        return self._run_wrapper(process_persistence_report.generate_process_persistence_report,
                                 "Process Persistence Report", browser_pref)

    def run_images_report(self, browser_pref=None):
        return self._run_wrapper(images_report.generate_images_report,
                                 "Images Report", browser_pref)

    def run_console_log_report(self, browser_pref=None):
        return self._run_wrapper(console_log_report.generate_console_log_report,
                                 "Console Log Report", browser_pref)

    def run_ping_report(self, browser_pref=None):
        return self._run_wrapper(ping_util_report.generate_ping_report,
                                 "Ping Report", browser_pref)

    def run_whois_report(self, browser_pref=None):
        return self._run_wrapper(whois_report.generate_whois_report,
                                 "WHOIS Report", browser_pref)

    def run_user_activity_report(self, browser_pref=None):
        return self._run_wrapper(user_activity_report.generate_user_activity_report,
                                 "User Activity Report (Downloads & Extensions)", browser_pref)

    def open_browser_tool(self, url):
        self.log(f"▶ Opening browser tool: {url}")
        import webbrowser
        webbrowser.open(url)

    def show_version_info(self):
        messagebox.showinfo("Version Info", "IRIS Incident Response Toolkit\nVersion: v3.2\n\nBuilt for rapid forensic triage.\n– SHIFTY")

if __name__ == "__main__":
    IRISGUI().mainloop()
