import sys
import re
import plistlib
from typing import Any, List, Dict

from ...helpers import MockAppInstance, Helpers

def get_interface_config(helpers: Helpers, app_instance: Any) -> List[Dict[str, Any]]:
    """
    Parses network interface configuration into structured list.
    Returns keys: name, device, mac_address, ipv4, ipv6, status
    """
    interfaces = []
    os_type = helpers.os_type
    
    try:
        if os_type == "darwin":
            # Use System Profiler for robust structured data
            xml = helpers.run_command("system_profiler -xml SPNetworkDataType", check_shell=True, app_instance=app_instance)
            if xml:
                try:
                    plist = plistlib.loads(xml.encode('utf-8'))
                    if plist and len(plist) > 0 and '_items' in plist[0]:
                        items = plist[0]['_items']
                        for item in items:
                            interfaces.append({
                                "name": item.get('_name', 'Unknown'),
                                "device": item.get('interface', 'N/A'),
                                "mac_address": item.get('hardware_address', 'N/A'),
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
        html_body += "<table><thead><tr><th>Name/Desc</th><th>Device</th><th>MAC Address</th><th>IPv4</th><th>IPv6</th></tr></thead><tbody>"
        for iface in interfaces:
            v4 = "<br/>".join(iface['ipv4']) if isinstance(iface['ipv4'], list) else iface['ipv4']
            v6 = "<br/>".join(iface['ipv6']) if isinstance(iface['ipv6'], list) else iface['ipv6']
            
            html_body += f"<tr><td>{iface['name']}</td><td>{iface['device']}</td><td>{iface['mac_address']}</td>"
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