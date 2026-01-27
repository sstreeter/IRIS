import sys
import re
from typing import Any, List, Dict

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers

def get_active_connections(helpers: Helpers, app_instance: Any) -> List[Dict[str, Any]]:
    """
    Parses active network connections into a structured list.
    Returns: List of dicts with keys: pid, process, protocol, local, remote, state
    """
    connections = []
    os_type = helpers.os_type
    
    try:
        if os_type == "darwin":
            # lsof -i -P -n
            # Output: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME
            raw = helpers.run_command("lsof -i -P -n", check_shell=True, app_instance=app_instance)
            if raw:
                lines = raw.splitlines()
                # Skip header if present
                start_idx = 1 if lines and lines[0].startswith('COMMAND') else 0
                
                for line in lines[start_idx:]:
                    parts = line.split()
                    if len(parts) >= 8:
                        # Basic heuristics
                        cmd = parts[0]
                        pid = parts[1]
                        proto = parts[4] if 'IP' in parts[4] else 'Unknown'
                        if proto == 'Unknown' and len(parts) > 5 and 'IP' in parts[5]: # Handle variable column widths sometimes
                             proto = parts[5]
                        
                        # Handle State at end
                        state = "UNKNOWN"
                        last_token = parts[-1]
                        address_token = last_token
                        
                        if last_token == "(LISTEN)":
                            state = "LISTEN"
                            address_token = parts[-2]
                        elif last_token == "(ESTABLISHED)":
                            state = "ESTABLISHED"
                            address_token = parts[-2]
                        elif last_token == "(CLOSED)":
                            state = "CLOSED"
                            address_token = parts[-2]
                        elif "->" in last_token:
                             state = "ESTABLISHED" # Implicit for arrows without explicit state
                             address_token = last_token
                        elif "*:" in last_token:
                             state = "LISTEN" # Implicit for wildcard
                             address_token = last_token
                        
                        # Parse Address
                        local = address_token
                        remote = ""
                        
                        if "->" in address_token:
                            splits = address_token.split("->")
                            local = splits[0]
                            remote = splits[1] if len(splits) > 1 else ""
                            
                        connections.append({
                            "pid": pid,
                            "process": cmd,
                            "protocol": proto,
                            "local": local,
                            "remote": remote,
                            "state": state,
                            "raw": line
                        })

        elif os_type == "linux":
            # ss -tulpn
            # Output: Netid State Recv-Q Send-Q Local_Address:Port Peer_Address:Port Process
            raw = helpers.run_command("ss -tulpn", check_shell=True, app_instance=app_instance)
            if raw:
                lines = raw.splitlines()
                start_idx = 1 if lines and lines[0].startswith('Netid') else 0
                
                for line in lines[start_idx:]:
                    parts = line.split()
                    if len(parts) >= 6:
                        proto = parts[0]
                        state = parts[1]
                        local = parts[4]
                        remote = parts[5]
                        process_info = parts[6] if len(parts) > 6 else ""
                        
                        # Extract PID/Name from users:(("process",pid=123,fd=4))
                        pid = ""
                        cmd = ""
                        if "users:" in process_info:
                             m = re.search(r'"([^"]+)",pid=(\d+)', process_info)
                             if m:
                                 cmd = m.group(1)
                                 pid = m.group(2)
                        
                        connections.append({
                            "pid": pid,
                            "process": cmd,
                            "protocol": proto.upper(),
                            "local": local,
                            "remote": remote,
                            "state": state,
                            "raw": line
                        })

        elif os_type == "win32":
            # netstat -ano
            # Output: Proto  Local Address          Foreign Address        State           PID
            raw = helpers.run_command("netstat -ano", check_shell=True, app_instance=app_instance)
            if raw:
                lines = raw.splitlines()
                # Skip headers (usually 4 lines)
                content_started = False
                for line in lines:
                    if not content_started:
                        if line.strip().startswith("Proto"):
                            content_started = True
                        continue
                        
                    parts = line.split()
                    if len(parts) >= 5:
                        proto = parts[0]
                        local = parts[1]
                        remote = parts[2]
                        state = parts[3]
                        pid = parts[4]
                        
                        # UDP sometimes doesn't have State in older netstat? 
                        # If len is 4, it might be UDP
                        if proto == "UDP" and len(parts) == 4:
                             state = "N/A"
                             pid = parts[3]
                             remote = parts[2] # actually *:*
                        
                        connections.append({
                            "pid": pid,
                            "process": "N/A", # Netstat doesn't give process name, would need tasklist
                            "protocol": proto,
                            "local": local,
                            "remote": remote,
                            "state": state,
                            "raw": line
                        })

    except Exception as e:
        app_instance.log_output(f"Error parsing connections: {e}")

    return connections

def generate_tcp_connections_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """
    Gathers and reports active TCP/UDP connections and listening ports.
    """
    app_instance.log_output("\n--- Generating TCP/UDP Connections Report ---")
    
    connections = get_active_connections(helpers, app_instance)
    
    html_body = "<h2>Active Network Connections & Listening Ports</h2>"
    
    if connections:
        html_body += "<table>"
        html_body += "<thead><tr><th>Proto</th><th>State</th><th>Local Address</th><th>Remote Address</th><th>Actions</th><th>Process</th><th>PID</th></tr></thead>"
        html_body += "<tbody>"
        
        # Sort by State (LISTEN first), then PID
        def sort_key(c):
            s = c['state']
            p = 0
            try: p = int(c['pid']) 
            except: pass
            state_rank = 0 if "LISTEN" in s else 1
            return (state_rank, p)
            
        for conn in sorted(connections, key=sort_key):
             # Investigation link
             remote_addr = conn['remote']
             actions = ""
             if remote_addr and remote_addr != "N/A" and "*:" not in remote_addr:
                 ip = remote_addr.split(':')[0]
                 if ip and not any(x in ip for x in ["127.0.0.1", "0.0.0.0", "::", "localhost"]):
                     actions = f"<a href='https://www.virustotal.com/gui/ip-address/{ip}' target='_blank' title='Check on VirusTotal'>🔍 VT</a>"

             html_body += f"<tr>"
             html_body += f"<td>{conn['protocol']}</td>"
             html_body += f"<td>{conn['state']}</td>"
             html_body += f"<td>{conn['local']}</td>"
             html_body += f"<td>{conn['remote']}</td>"
             html_body += f"<td>{actions}</td>"
             html_body += f"<td>{conn['process']}</td>"
             html_body += f"<td>{conn['pid']}</td>"
             html_body += f"</tr>"
             
        html_body += "</tbody></table>"
        html_body += f"<p>Total Connections Found: {len(connections)}</p>"
    else:
        html_body += "<p>No active connections found or tool execution failed.</p>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "TCP_Connections_Report.html", 
        "TCP-UDP Connections Report", 
        html_body,
        browser_preference=browser_preference
    )