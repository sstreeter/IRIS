import sys
import re
import plistlib
from typing import Any, List, Dict

from ...helpers import MockAppInstance, Helpers

from .mac_vendor_util import MacVendorLookup

MAC_VENDOR_MAP = {
    "00:0c:29": "VMware",
    "00:50:56": "VMware",
    "00:05:69": "VMware",
    "08:00:27": "VirtualBox",
    "ac:de:48": "Apple",
    "f0:18:98": "Apple",
    "74:a6:cd": "Apple",
    "ac:b4:80": "Apple",
    "00:25:00": "Apple",
    "00:26:bb": "Apple",
    "00:03:93": "Apple",
    "3c:15:c2": "Apple",
    "b8:c7:5d": "Apple",
    "00:1c:42": "Parallels",
    "00:15:5d": "Microsoft",
    "00:1a:11": "Google",
    "3c:5a:b4": "Google",
    "00:50:b6": "Belkin",
    "00:e0:4c": "Realtek",
    "00:1e:10": "Shenzhen Mercury",
    "d8:eb:97": "TP-Link",
    "e8:94:f6": "TP-Link",
    "00:14:22": "Dell",
    "00:21:70": "Dell",
    "00:13:21": "HP",
    "00:17:a4": "HP",
    "00:1a:4b": "HP",
    "b4:b5:b6": "Intel",
    "00:1d:e1": "Intel",
    "00:1b:21": "Intel",
}

def correlate_mac_vendor(mac: str) -> str:
    if not mac or mac == "N/A":
        return "Unknown"
    # Normalize and take OUI
    clean_mac = mac.lower().replace("-", ":")
    oui = ":".join(clean_mac.split(":")[:3])
    
    # 1. Fast Path: Check static common vendors (VMs, Apple)
    static_vendor = MAC_VENDOR_MAP.get(oui)
    if static_vendor:
        return static_vendor
        
    # 2. Deep Lookup: Use API
    return MacVendorLookup.lookup(mac)

def get_mac_address_map(helpers: Helpers, app_instance: Any) -> Dict[str, str]:
    """
    Builds a reliable map of DeviceID -> MAC Address using:
    1. networksetup (Primary, for physical/listed ports)
    2. ifconfig (Secondary, for virtual bridges/interfaces)
    """
    mac_map = {}
    
    # 1. Parse networksetup
    try:
        ns_out = helpers.run_command("networksetup -listallhardwareports", check_shell=True, app_instance=app_instance)
        if ns_out:
            # Output format:
            # Hardware Port: Wi-Fi
            # Device: en0
            # Ethernet Address: 00:00:00:00:00:00
            
            lines = ns_out.splitlines()
            current_device = None
            for line in lines:
                if "Device:" in line:
                    current_device = line.split(":", 1)[1].strip()
                elif "Ethernet Address:" in line and current_device:
                    mac = line.split(":", 1)[1].strip()
                    if mac:
                        mac_map[current_device] = mac
                    current_device = None
    except Exception as e:
        app_instance.log_output(f"Error running networksetup: {e}")

    # 2. Parse ifconfig fallback (for virtual bridges not in networksetup)
    try:
        if_out = helpers.run_command("ifconfig", check_shell=True, app_instance=app_instance)
        if if_out:
            # en0: flags=...
            #         ether 00:00:00:00:00:00 
            current_iface = None
            for line in if_out.splitlines():
                if not line.startswith("\t") and ":" in line:
                    current_iface = line.split(":")[0]
                elif current_iface and ("ether " in line or "lladdr " in line):
                     tokens = line.strip().split()
                     if len(tokens) >= 2:
                         mac = tokens[1]
                         if current_iface not in mac_map: # Don't overwrite networksetup as it's cleaner
                             mac_map[current_iface] = mac
    except Exception as e:
        app_instance.log_output(f"Error running ifconfig: {e}")
        
    return mac_map

def get_interface_config(helpers: Helpers, app_instance: Any) -> List[Dict[str, Any]]:
    """
    Parses network interface configuration into structured list.
    Returns keys: name, device, mac_address, ipv4, ipv6, status
    """
    interfaces = []
    os_type = helpers.os_type
    
    try:
        if os_type == "darwin":
            # 1. Get MAC Map first
            mac_map = get_mac_address_map(helpers, app_instance)
            
            # 2. Use System Profiler for structure and IPs
            xml = helpers.run_command("system_profiler -xml SPNetworkDataType", check_shell=True, app_instance=app_instance)
            if xml:
                try:
                    plist = plistlib.loads(xml.encode('utf-8'))
                    if plist and len(plist) > 0 and '_items' in plist[0]:
                        items = plist[0]['_items']
                        for item in items:
                            device_id = item.get('interface', 'N/A')
                            
                            # Resolve MAC
                            mac = item.get('hardware_address', 'N/A')
                            if mac == 'N/A' and device_id in mac_map:
                                mac = mac_map[device_id]
                            
                            # Fallback if mapped but still generic:
                            if device_id in mac_map and mac == 'N/A':
                                 mac = mac_map[device_id]

                            interfaces.append({
                                "name": item.get('_name', 'Unknown'),
                                "device": device_id,
                                "mac_address": mac,
                                "vendor": correlate_mac_vendor(mac),
                                "ipv4": item.get('ip_address', []), 
                                "ipv6": item.get('ipv6_address', []),
                                "status": "Active" if item.get('ip_address') else "Inactive" 
                            })
                except Exception as e:
                    app_instance.log_output(f"Error parsing Network XML: {e}")

        elif os_type == "linux":
            # Parse 'ip addr'
            raw = helpers.run_command("ip addr", check_shell=True, app_instance=app_instance)
            if raw:
                # Simple parser for ip addr blocks
                current_iface = {}
                for line in raw.splitlines():
                    # Start of block: 2: eth0: ...
                    m_start = re.match(r'^\d+: ([^:]+):', line)
                    if m_start:
                        if current_iface: interfaces.append(current_iface)
                        current_iface = {
                            "name": m_start.group(1).strip(),
                            "device": m_start.group(1).strip(),
                            "mac_address": "N/A",
                            "ipv4": [],
                            "ipv6": [],
                            "status": "Unknown"
                        }
                    elif current_iface:
                        # Extract IPs and MAC
                        line = line.strip()
                        if line.startswith("link/ether"):
                            tokens = line.split()
                            if len(tokens) > 1: current_iface["mac_address"] = tokens[1]
                        elif line.startswith("inet "):
                            tokens = line.split()
                            if len(tokens) > 1: current_iface["ipv4"].append(tokens[1])
                        elif line.startswith("inet6 "):
                            tokens = line.split()
                            if len(tokens) > 1: current_iface["ipv6"].append(tokens[1])
                
                if current_iface: interfaces.append(current_iface)

        elif os_type == "win32":
            # Parse ipconfig /all
            raw = helpers.run_command("ipconfig /all", check_shell=True, app_instance=app_instance)
            if raw:
                current_iface = {}
                for line in raw.splitlines():
                    line = line.rstrip()
                    if not line: continue
                    
                    if not line.startswith(" ") and (line.endswith(":") or "adapter" in line):
                         # Header: "Ethernet adapter Ethernet:"
                         if current_iface: interfaces.append(current_iface)
                         name_dirty = line.replace(":", "").strip()
                         current_iface = {
                             "name": name_dirty,
                             "device": "N/A",
                             "mac_address": "N/A",
                             "ipv4": [],
                             "ipv6": [],
                             "status": "Unknown"
                         }
                    elif current_iface:
                        # Properties
                        if ":" in line:
                            key, val = line.split(":", 1)
                            key = key.strip().lower()
                            val = val.strip()
                            # remove (Preferred) suffix
                            val = re.sub(r'\(.*\)', '', val).strip()
                            
                            if "physical address" in key:
                                current_iface["mac_address"] = val
                            elif "ipv4 address" in key:
                                current_iface["ipv4"].append(val)
                            elif "ipv6 address" in key:
                                current_iface["ipv6"].append(val)
                                
                if current_iface: interfaces.append(current_iface)

    except Exception as e:
        app_instance.log_output(f"Error parsing network config: {e}")
        
    return interfaces

def generate_network_config_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Gathers and reports detailed network configuration for the host OS."""
    app_instance.log_output("\n--- Generating Network Configuration Report ---")
    
    interfaces = get_interface_config(helpers, app_instance)
    
    html_body = "<h2>Network Interfaces</h2>"
    
    if interfaces:
        html_body += "<table><thead><tr><th>Name/Desc</th><th>Device</th><th>MAC Address</th><th>Vendor</th><th>IPv4</th><th>IPv6</th></tr></thead><tbody>"
        for iface in interfaces:
            v4 = "<br/>".join(iface['ipv4']) if isinstance(iface['ipv4'], list) else iface['ipv4']
            v6 = "<br/>".join(iface['ipv6']) if isinstance(iface['ipv6'], list) else iface['ipv6']
            vendor = iface.get('vendor', 'Unknown')
            
            html_body += f"<tr><td>{iface['name']}</td><td>{iface['device']}</td><td>{iface['mac_address']}</td><td>{vendor}</td>"
            html_body += f"<td>{v4}</td><td>{v6}</td></tr>"
        html_body += "</tbody></table>"
    else:
        html_body += "<p>No network interfaces found.</p>"

    # DNS Info (Appended as raw for now as it doesn't fit table well)
    html_body += "<h3>DNS Configuration</h3>"
    dns_cmd = "scutil --dns" if helpers.os_type == "darwin" else ("cat /etc/resolv.conf" if helpers.os_type == "linux" else None)
    if dns_cmd:
         out = helpers.run_command(dns_cmd, check_shell=True, app_instance=app_instance)
         if out: html_body += f"<pre>{out}</pre>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Network_Config_Report.html", 
        "Network Configuration Report", 
        html_body,
        browser_preference=browser_preference
    )