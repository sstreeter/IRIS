import tkinter as tk
from tkinter import ttk, messagebox
import re
from typing import List, Dict, Any

class NetworkManagerDialog(tk.Toplevel):
    def __init__(self, parent, helpers, app_instance):
        super().__init__(parent)
        self.title("IRIS Network Manager")
        self.geometry("600x500")
        self.helpers = helpers
        self.app_instance = app_instance
        self.interfaces = []
        
        self._build_ui()
        self.refresh_interfaces()
        
        # Center the dialog
        self.transient(parent)
        self.grab_set()
        
    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#f8f9fa", pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text="Network Interface Control", font=("Arial", 14, "bold"), bg="#f8f9fa").pack()
        tk.Label(header, text="Selectively disable/enable interfaces or use the Kill Switch.", bg="#f8f9fa", fg="#666").pack()
        
        # Emergency Kill Switch
        kill_frame = tk.Frame(self, pady=10, padx=20)
        kill_frame.pack(fill=tk.X)
        self.btn_kill = tk.Button(kill_frame, text="☢️ KILL ALL NETWORK INTERFACES", 
                                  bg="#dc3545", fg="white", font=("Arial", 11, "bold"),
                                  command=self.kill_all_networks, height=2)
        self.btn_kill.pack(fill=tk.X)
        
        # Interface List
        list_frame = tk.LabelFrame(self, text="Detected Interfaces", padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Refresh Button
        tk.Button(self, text="🔄 Refresh Interface Status", command=self.refresh_interfaces).pack(pady=10)

    def refresh_interfaces(self):
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        self.interfaces = self._get_interfaces()
        
        if not self.interfaces:
            tk.Label(self.scrollable_frame, text="No interfaces found.", fg="#999").pack(pady=20)
            return

        # Headers
        h_frame = tk.Frame(self.scrollable_frame)
        h_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(h_frame, text="Interface", width=25, anchor="w", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        tk.Label(h_frame, text="Device", width=10, anchor="w", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        tk.Label(h_frame, text="Status", width=15, anchor="w", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        tk.Label(h_frame, text="Action", width=10, anchor="w", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        ttk.Separator(self.scrollable_frame, orient="horizontal").pack(fill=tk.X, pady=(0, 10))

        for iface in self.interfaces:
            row = tk.Frame(self.scrollable_frame, pady=5)
            row.pack(fill=tk.X)
            
            # Icon calc
            icon = "🔌"
            if "Wi-Fi" in iface['name']: icon = "🛜"
            elif "Bridge" in iface['name']: icon = "🌉"
            elif "Thunderbolt" in iface['name']: icon = "⚡"
            elif "USB" in iface['name']: icon = "🔗"
            
            # Status calc
            is_up = iface['status'] == 'UP'
            status_text = "ACTIVE" if is_up else "DISABLED"
            status_color = "#28a745" if is_up else "#dc3545"
            
            tk.Label(row, text=f"{icon} {iface['name']}", width=25, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=iface['device'], width=10, anchor="w", fg="#666").pack(side=tk.LEFT)
            tk.Label(row, text=status_text, width=15, anchor="w", fg=status_color, font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            
            # Action Button
            btn_text = "Disable" if is_up else "Enable"
            btn_color = "#ffdddd" if is_up else "#ddffdd" # Subtle BG
            cmd = lambda i=iface: self.toggle_interface(i)
            
            tk.Button(row, text=btn_text, command=cmd, bg=btn_color, width=8, font=("Arial", 9)).pack(side=tk.LEFT)

    def _get_interfaces(self) -> List[Dict[str, Any]]:
        """Parses networksetup output to find hardware ports."""
        interfaces = []
        
        # Run networksetup -listallhardwareports
        # Output format:
        # Hardware Port: Wi-Fi
        # Device: en0
        # ...
        raw = self.helpers.run_command(["networksetup", "-listallhardwareports"])
        
        current_port = None
        device_map = {} # device -> name
        
        for line in raw.splitlines():
            if line.startswith("Hardware Port:"):
                current_port = line.split(": ")[1].strip()
            elif line.startswith("Device:") and current_port:
                device = line.split(": ")[1].strip()
                device_map[device] = current_port
                current_port = None
                
        # Now check status for each
        for dev, name in device_map.items():
            status = "DOWN"
            
            # Method 1: Check ifconfig for UP flag
            ifconfig = self.helpers.run_command(["ifconfig", dev])
            # flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
            if "<UP," in ifconfig or "flags=" in ifconfig and "UP" in ifconfig.split("<")[1].split(">")[0]:
                status = "UP"
            
            # Special check for Wi-Fi power off (might be UP but power off?)
            if "Wi-Fi" in name:
                wifi_status = self.helpers.run_command(["networksetup", "-getairportpower", dev])
                if "Off" in wifi_status:
                    status = "DOWN"

            interfaces.append({
                "name": name,
                "device": dev,
                "status": status
            })
            
        return interfaces

    def toggle_interface(self, iface):
        """Toggles a single interface."""
        name = iface['name']
        dev = iface['device']
        is_up = iface['status'] == 'UP'
        action = "Disable" if is_up else "Enable"
        
        if not messagebox.askyesno(f"Confirm {action}", f"Are you sure you want to {action} {name} ({dev})?"):
            return

        cmd = ""
        success_msg = ""
        
        # Wi-Fi Logic (Cleanest)
        if "Wi-Fi" in name:
            state = "off" if is_up else "on"
            cmd = f"networksetup -setairportpower {dev} {state}"
            # networksetup usually doesn't need sudo for power, but sometimes it does. 
            # safe to run as standard user usually, but let's try helpers.run_command first.
            # If it fails, maybe sudo? Actually networksetup -setairportpower often requires admin.
            # We will use sudo command just to be safe if standard fails? 
            # Let's assume we use sudo for consistency in IRIS context.
            self.helpers.run_sudo_command(cmd, prompt_text=f"IRIS needs Admin privileges to toggle Wi-Fi.")
            
        else:
            # Wired/Other Logic (ifconfig)
            state = "down" if is_up else "up"
            cmd = f"ifconfig {dev} {state}"
            self.helpers.run_sudo_command(cmd, prompt_text=f"IRIS needs Admin privileges to toggle {name}.")
            
        self.refresh_interfaces()

    def kill_all_networks(self):
        """Disables ALL interfaces."""
        if not messagebox.askyesno("CONFIRM KILL SWITCH", "Are you sure you want to DISABLE ALL INTERFACES?\n\nThis will cut all network connectivity immediately.", icon='warning'):
            return
            
        count = 0
        for iface in self.interfaces:
            if iface['status'] == 'UP':
                name = iface['name']
                dev = iface['device']
                
                print(f"Disabling {name} ({dev})...")
                
                if "Wi-Fi" in name:
                    self.helpers.run_command(f"networksetup -setairportpower {dev} off")
                else:
                    self.helpers.run_sudo_command(f"ifconfig {dev} down", prompt_text="IRIS needs Admin privileges to execute Kill Switch.")
                count += 1
                
        messagebox.showinfo("Kill Switch Executed", f"Attempted to disable {count} active interfaces.")
        self.refresh_interfaces()
