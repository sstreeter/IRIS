import platform
import sys
import re
import plistlib
import shutil
from typing import List, Optional, Dict, Any, Union

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers, DiskInfo
from ...analysis.security_advisor import SecurityAdvisor

def get_system_data(helpers: Helpers, app_instance: Any) -> Dict[str, Any]:
    """Collects system information into a dictionary."""
    data = {
        "os_type": helpers.os_type,
        "general": {
            "system": platform.system(),
            "node": platform.node(),
            "machine": platform.machine(),
            "processor_generic": platform.processor(),
            "details": {}
        },
        "memory": {
            "total_gb": 0,
            "used_gb": 0,
            "available_gb": 0,
            "swap_total": "N/A",
            "swap_used": "N/A",
            "swap_free": "N/A",
            "details": {}
        },
        "storage": []
    }

    # --- Windows Collection ---
    if helpers.os_type == "windows":
        app_instance.log_output("Gathering detailed Windows system information...")
        output_os = helpers.run_command('systeminfo', app_instance=app_instance) # Simplified command to parse locally if needed, or stick to findstr
        # Staying with findstr for efficiency as per original, but capturing output
        output_os_filtered = helpers.run_command('systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Manufacturer" /C:"System Model" /C:"Processor(s)" /C:"Total Physical Memory"', app_instance=app_instance)
        if output_os_filtered:
            for line in output_os_filtered.strip().split('\n'):
                if ":" in line:
                    attr, val = line.split(":", 1)
                    data["general"]["details"][attr.strip()] = val.strip()

        # Memory
        wmic_mem = helpers.run_command("wmic ComputerSystem get TotalPhysicalMemory", app_instance=app_instance)
        if wmic_mem:
            try:
                # wmic output usually Header \n Value
                parts = wmic_mem.strip().split()
                if len(parts) > 1:
                    data["memory"]["total_gb"] = round(int(parts[-1]) / (1024**3), 2)
            except: pass
        
        # Storage
        wmic_disk_output = helpers.run_command("wmic diskdrive get Caption,SerialNumber,Size,InterfaceType /format:list", app_instance=app_instance)
        if wmic_disk_output:
            current_disk = {}
            for line in wmic_disk_output.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    current_disk[key.strip()] = value.strip()
                elif not line.strip() and current_disk:
                    size = int(current_disk.get('Size', 0))
                    data["storage"].append({
                        "name": current_disk.get('Caption'),
                        "type": "Physical Disk",
                        "size_gb": round(size / (1024**3), 2),
                        "used": "N/A", "available": "N/A",
                        "filesystem": "N/A", "mount_point": "N/A",
                        "serial": current_disk.get('SerialNumber')
                    })
                    current_disk = {}
            if current_disk: # Catch last one
                 size = int(current_disk.get('Size', 0))
                 data["storage"].append({
                    "name": current_disk.get('Caption'),
                    "type": "Physical Disk",
                    "size_gb": round(size / (1024**3), 2),
                    "used": "N/A", "available": "N/A",
                    "filesystem": "N/A", "mount_point": "N/A",
                    "serial": current_disk.get('SerialNumber')
                })

    # --- macOS Collection ---
    elif helpers.os_type == "darwin":
        app_instance.log_output("Gathering detailed macOS system information...")
        sw_info = helpers.run_command("system_profiler SPSoftwareDataType", check_shell=True, app_instance=app_instance)
        if sw_info:
            for pattern in [r'System Version: (.+)', r'Build Version: (.+)']:
                m = re.search(pattern, sw_info)
                if m: data["general"]["details"][pattern.split(':')[0]] = m.group(1).strip()
        
        hw_info = helpers.run_command("system_profiler SPHardwareDataType", check_shell=True, app_instance=app_instance)
        if hw_info:
            for pattern in [r'Processor Name: (.+)', r'Processor Speed: (.+)', r'Total Number of Cores: (.+)']:
                m = re.search(pattern, hw_info)
                if m: data["general"]["details"][pattern.split(':')[0]] = m.group(1).strip()

        # Memory
        mem_size = helpers.run_command("sysctl -n hw.memsize", check_shell=True, app_instance=app_instance)
        if mem_size:
            data["memory"]["total_gb"] = round(int(mem_size.strip()) / (1024**3), 2)
        
        vm_stat = helpers.run_command("vm_stat", check_shell=True, app_instance=app_instance)
        if vm_stat:
            # Simple parsing for active/wired to approx used
            lines = vm_stat.splitlines()
            p_size = 4096 # default
            stats = {}
            for line in lines:
                if "page size" in line:
                    m = re.search(r'(\d+)', line)
                    if m: p_size = int(m.group(1))
                else:
                    m = re.match(r'\s*Pages\s+(.+?):\s+(\d+)', line)
                    if m: stats[m.group(1).strip('.')] = int(m.group(2))
            
            # Approximate used = active + wired + compressed
            used_pages = stats.get('active', 0) + stats.get('wired down', 0) + stats.get('occupied by physical pages that have been compressed', 0)
            data["memory"]["used_gb"] = round((used_pages * p_size) / (1024**3), 2)
            if data["memory"]["total_gb"]:
                 data["memory"]["available_gb"] = round(data["memory"]["total_gb"] - data["memory"]["used_gb"], 2)

        # Storage
        try:
            disk_plist_raw = helpers.run_command("diskutil list -plist", check_shell=True, app_instance=app_instance)
            if disk_plist_raw:
                 plist = plistlib.loads(disk_plist_raw.encode('utf-8'))
                 
                 def process_disk_entry(entry):
                     # Process current entry
                     disk_name = entry.get('DeviceIdentifier', 'N/A')
                     mount_point = entry.get('MountPoint', 'N/A')
                     size_gb = round(entry.get('Size', 0)/(1024**3), 2)
                     
                     # Check usage if mounted
                     used = "N/A"
                     avail = "N/A"
                     if mount_point and mount_point != "N/A":
                         # Get usage via df
                         df_out = helpers.run_command(f"df -h \"{mount_point}\"", check_shell=True, app_instance=app_instance)
                         if df_out:
                             lines = df_out.splitlines()
                             if len(lines) > 1:
                                 # Filesystem Size Used Avail Capacity iused ifree %iused  Mounted on
                                 # We want Used and Avail. 
                                 # map /dev/disk1s1s1   460Gi   15Gi  276Gi     6% ... /
                                 parts = lines[1].split()
                                 if len(parts) >= 4:
                                     used = parts[2]
                                     avail = parts[3]

                     is_internal = entry.get('Internal', True)
                     is_ejectable = entry.get('Ejectable', False)
                     
                     # Determine descriptive type
                     # Physical Disk vs Partition
                     type_str = "Partition" if "Partitions" not in entry else "Physical Disk"
                     
                     # Add physical characteristics if it's a disk
                     details_str = ""
                     if "Partitions" in entry:
                         details_str = "Internal" if is_internal else "External"
                         if is_ejectable: details_str += ", Removable"

                     data["storage"].append({
                         "name": disk_name,
                         "type": type_str,
                         "details": details_str,
                         "size_gb": size_gb,
                         "mount_point": mount_point,
                         "used": used,
                         "available": avail,
                         "serial": "N/A" # Simplify
                     })
                     
                     # Recurse
                     if "Partitions" in entry:
                         for part in entry["Partitions"]:
                             process_disk_entry(part)

                 for disk in plist.get('AllDisksAndPartitions', []):
                     process_disk_entry(disk)
        except Exception as e:
            app_instance.log_output(f"Error parsing storage: {e}")

    # --- Linux Collection ---
    elif helpers.os_type == "linux":
        app_instance.log_output("Gathering Linux system information...")
        
        # Distro Info
        distro_name = helpers.get_linux_distro()
        data["general"]["details"]["Distro"] = distro_name
        
        # Kernel
        kernel = helpers.run_command("uname -r", app_instance=app_instance).strip()
        data["general"]["details"]["Kernel"] = kernel

        # CPU info from lscpu or /proc/cpuinfo
        cpu_info = helpers.run_command("lscpu", app_instance=app_instance)
        if cpu_info:
            for line in cpu_info.splitlines():
                if "Model name:" in line:
                    data["general"]["details"]["Processor"] = line.split(":", 1)[1].strip()
                if "CPU(s):" in line:
                    data["general"]["details"]["Cores"] = line.split(":", 1)[1].strip()

        # Memory (free -m)
        free_m = helpers.run_command("free -m", app_instance=app_instance)
        if free_m:
            lines = free_m.splitlines()
            if len(lines) > 1:
                mem_parts = lines[1].split()
                # Mem: Total Used Free ...
                data["memory"]["total_gb"] = round(int(mem_parts[1]) / 1024, 2)
                data["memory"]["used_gb"] = round(int(mem_parts[2]) / 1024, 2)
                data["memory"]["available_gb"] = round(int(mem_parts[-1]) / 1024, 2) # Available is usually last

        # Storage (lsblk -J or df -h)
        # Using lsblk for structured output if available, else df
        lsblk = helpers.run_command("lsblk -J", app_instance=app_instance)
        if lsblk and lsblk.startswith('{'):
             # Parse JSON if possible (requires json import, let's skip import for now and use df text parsing for safety)
             pass
        
        df_h = helpers.run_command("df -h", app_instance=app_instance)
        if df_h:
            for line in df_h.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 6:
                     data["storage"].append({
                         "name": parts[0],
                         "mount_point": parts[-1],
                         "size_gb": parts[1], # String with Unit
                         "used": parts[2],
                         "available": parts[3],
                         "type": "Filesystem"
                     })

    return data

def generate_system_hardware_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    app_instance.log_output("\n--- Generating System & Hardware Report ---")
    
    # 1. Collect Data
    data = get_system_data(helpers, app_instance)
    
    # 2. Build HTML from Data
    html_body = ""
    
    # General
    html_body += "<h2>General System Information</h2><table><tr><th>Attribute</th><th>Value</th></tr>"
    html_body += f"<tr><td>System</td><td>{data['general']['system']}</td></tr>"
    html_body += f"<tr><td>Node Name</td><td>{data['general']['node']}</td></tr>"
    html_body += f"<tr><td>Machine</td><td>{data['general']['machine']}</td></tr>"
    for k, v in data['general']['details'].items():
        html_body += f"<tr><td>{k}</td><td>{v}</td></tr>"
    html_body += "</table>"

    # Memory
    html_body += "<h2>Memory (RAM) Information</h2><table><tr><th>Metric</th><th>Value</th></tr>"
    html_body += f"<tr><td>Total Memory</td><td>{data['memory']['total_gb']} GB</td></tr>"
    html_body += f"<tr><td>Used Memory</td><td>{data['memory']['used_gb']} GB</td></tr>"
    html_body += f"<tr><td>Available Memory</td><td>{data['memory']['available_gb']} GB</td></tr>"
    html_body += "</table>"

    # Storage
    html_body += "<h2>Storage Information</h2><table><tr><th>Drive</th><th>Type</th><th>Details</th><th>Size</th><th>Used</th><th>Available</th><th>Mount</th></tr>"
    for disk in data['storage']:
        name = disk.get('name', 'N/A')
        dtype = disk.get('type', 'N/A')
        details = disk.get('details', '')
        size = disk.get('size_gb', 'N/A')
        if isinstance(size, float): size = f"{size} GB"
        used = disk.get('used', 'N/A')
        avail = disk.get('available', 'N/A')
        mount = disk.get('mount_point', 'N/A')
        html_body += f"<tr><td>{name}</td><td>{dtype}</td><td>{details}</td><td>{size}</td><td>{used}</td><td>{avail}</td><td>{mount}</td></tr>"
    html_body += "</table>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "System_Hardware_Report.html", 
        "System & Hardware Information Report", 
        html_body,
        browser_preference=browser_preference
    )

    # --- Security Advisor Analysis ---
    advisor = SecurityAdvisor()
    advisor.analyze_system_data(data)
    advisor_html = advisor.generate_report()
    
    # Append Advisor findings to the main report (or we could make it a separate section/file)
    # For now, let's append it to the existing HTML body effectively by regenerating it 
    # OR better, just add it to the html_body before the generate call.
    # Let's simple re-call generate with the appended body for this proof of concept.
    
    html_body += "<br><hr>" + advisor_html
    
    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "System_Hardware_Report.html", 
        "System & Hardware Information Report", 
        html_body,
        browser_preference=browser_preference
    )

