import re
from typing import Any, Dict
from ...helpers import Helpers, MockAppInstance

def parse_ping_output(raw_output: str) -> Dict[str, Any]:
    """
    Parses the output of the 'ping -c 4' command on macOS.
    """
    results = {
        "packets_transmitted": "N/A",
        "packets_received": "N/A",
        "packet_loss": "N/A",
        "min_latency": "N/A",
        "avg_latency": "N/A",
        "max_latency": "N/A",
        "stddev": "N/A",
        "raw": raw_output
    }
    
    if not raw_output:
        return results
        
    # Example stats line: 4 packets transmitted, 4 packets received, 0.0% packet loss
    stats_match = re.search(r'(\d+) packets transmitted, (\d+) packets received, ([\d\.]+)% packet loss', raw_output)
    if stats_match:
        results["packets_transmitted"] = stats_match.group(1)
        results["packets_received"] = stats_match.group(2)
        results["packet_loss"] = stats_match.group(3) + "%"
        
    # Example round-trip line: round-trip min/avg/max/stddev = 0.041/0.052/0.065/0.010 ms
    rt_match = re.search(r'round-trip min/avg/max/stddev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+) ms', raw_output)
    if rt_match:
        results["min_latency"] = rt_match.group(1) + " ms"
        results["avg_latency"] = rt_match.group(2) + " ms"
        results["max_latency"] = rt_match.group(3) + " ms"
        results["stddev"] = rt_match.group(4) + " ms"
        
    return results

def generate_ping_report(app_instance: Any, helpers: Helpers, target: str = None, browser_preference: str = "System Default"):
    """
    Prompts the user for a ping target (if not provided) and generates a report.
    """
    app_instance.log_output("\n--- Generating Ping Utility Report ---")
    
    if not target:
        target = helpers.ask_user_input(
            "Enter IP address or Hostname to ping:", 
            default_answer="8.8.8.8", 
            timeout=20, 
            app_instance=app_instance
        )
    
    if not target or target == "Cancelled":
        app_instance.log_output("Ping cancelled by user or timed out.")
        return

    app_instance.log_output(f"Pinging {target}...")
    # -c 4: send 4 packets, -W 1000: wait 1s for response
    raw_out = helpers.run_command(f"ping -c 4 -W 1000 {target}", check_shell=True, app_instance=app_instance)
    
    parsed = parse_ping_output(raw_out)
    
    html_body = f"<h2>Ping Results for: {target}</h2>"
    
    # Summary Table
    html_body += """
    <table>
        <thead>
            <tr>
                <th>Packets Transmitted</th>
                <th>Packets Received</th>
                <th>Packet Loss</th>
                <th>Min Latency</th>
                <th>Avg Latency</th>
                <th>Max Latency</th>
            </tr>
        </thead>
        <tbody>
            <tr>
    """
    html_body += f"<td>{parsed['packets_transmitted']}</td>"
    html_body += f"<td>{parsed['packets_received']}</td>"
    html_body += f"<td>{parsed['packet_loss']}</td>"
    html_body += f"<td>{parsed['min_latency']}</td>"
    html_body += f"<td>{parsed['avg_latency']}</td>"
    html_body += f"<td>{parsed['max_latency']}</td>"
    html_body += """
            </tr>
        </tbody>
    </table>
    """
    
    html_body += "<h3>Raw Command Output</h3>"
    html_body += f"<pre>{parsed['raw'] if parsed['raw'] else 'No output returned.'}</pre>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        f"Ping_Report_{target.replace('.', '_')}.html", 
        f"Ping Report - {target}", 
        html_body,
        browser_preference=browser_preference
    )
