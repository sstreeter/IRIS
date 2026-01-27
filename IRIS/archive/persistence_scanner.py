import psutil
import concurrent.futures
import re
from datetime import datetime

# --- Configurable whitelist of safe patterns ---
WHITELIST_PATTERNS = [
    r'/Applications/Adobe Creative Cloud/.*',
    r'/System/Library/.*',
    r'/usr/libexec/biomesyncd',
    r'com\.apple\.',  # Apple system services
    r'/usr/bin/osascript',
    r'/usr/bin/python3',
    r'/Applications/Activity Monitor.app/.*',
    r'/Applications/Adobe Acrobat Reader DC.app/.*',
    r'/Applications/Adobe Illustrator 2023.app/.*',
    r'/Applications/Adobe Photoshop 2023.app/.*',
    r'/Applications/Archive Utility.app/.*',
    r'/Applications/Audio MIDI Setup.app/.*',
    r'/Applications/Automator.app/.*',
    r'/Applications/Books.app/.*',
    r'/Applications/Box.app/.*',
    r'/Applications/Calculator.app/.*',
    r'/Applications/Calendar.app/.*',
    r'/Applications/Chess.app/.*',
    r'/Applications/ColorSync Utility.app/.*',
    r'/Applications/Console.app/.*',
    r'/Applications/Contacts.app/.*',
    r'/Applications/Dictionary.app/.*',
    r'/Applications/Discord.app/.*',
    r'/Applications/Dropbox.app/.*',
    r'/Applications/FaceTime.app/.*',
    r'/Applications/Final Cut Pro.app/.*',
    r'/Applications/Firefox.app/.*',
    r'/Applications/Font Book.app/.*',
    r'/Applications/Google Chrome.app/.*',
    r'/Applications/Google Drive.app/.*',
    r'/Applications/Keychain Access.app/.*',
    r'/Applications/Mail.app/.*',
    r'/Applications/Maps.app/.*',
    r'/Applications/Messages.app/.*',
    r'/Applications/Music.app/.*',
    r'/Applications/Network Utility.app/.*',
    r'/Applications/News.app/.*',
    r'/Applications/Notes.app/.*',
    r'/Applications/OneDrive.app/.*',
    r'/Applications/Photos.app/.*',
    r'/Applications/Podcasts.app/.*',
    r'/Applications/Preview.app/.*',
    r'/Applications/QuickTime Player.app/.*',
    r'/Applications/Reminders.app/.*',
    r'/Applications/Safari.app/.*',
    r'/Applications/Script Editor.app/.*',
    r'/Applications/Shortcuts.app/.*',
    r'/Applications/Signal.app/.*',
    r'/Applications/Slack.app/.*',
    r'/Applications/Spotify.app/.*',
    r'/Applications/Stocks.app/.*',
    r'/Applications/System Information.app/.*',
    r'/Applications/System Preferences.app/.*',
    r'/Applications/Telegram.app/.*',
    r'/Applications/Terminal.app/.*',
    r'/Applications/Time Machine.app/.*',
    r'/Applications/TV.app/.*',
    r'/Applications/Utilities/.*',
    r'/Applications/Visual Studio Code.app/.*',
    r'/Applications/Voice Memos.app/.*',
    r'/Applications/VoiceOver Utility.app/.*',
    r'/Applications/Weather.app/.*',
    r'/Applications/Xcode.app/.*',
    r'/Applications/Zoom.us.app/.*',
    r'/Applications/1Password.app/.*',
    r'/Applications/BBEdit.app/.*',
    r'/Applications/Brave Browser.app/.*',
    r'/Library/Application Support/Adobe/.*',
    r'/Library/Application Support/Google/.*',
    r'/Library/Application Support/Box/.*',
    r'/Library/Application Support/Dropbox/.*',
    r'/Library/Application Support/OneDrive/.*',
    r'/Library/Application Support/Slack/.*',
    r'/Library/Application Support/Spotify/.*',
    r'/Library/Application Support/Zoom/.*',
    r'/Library/Application Support/1Password/.*',
    r'/Library/Application Support/BraveSoftware/Brave-Browser/.*',
    r'/Library/Application Support/Visual Studio Code/.*',
    r'/Library/Google/.*',
    r'/Library/Preferences/com\.apple\.*',

    r'/Library/Frameworks/.*',
    r'/Applications/.*'
    r'/Library/Application Support/.*',
    r'~/.vscode/.*',
    r'~/Library/Application Support/.*',
    # Add more known safe paths or command patterns here
]

def is_whitelisted(cmdline, exe_path):
    """
    Returns True if cmdline or exe_path matches any whitelist pattern
    """
    combined = ' '.join(cmdline) if isinstance(cmdline, list) else cmdline or ''
    target_strings = [combined, exe_path or '']
    for pattern in WHITELIST_PATTERNS:
        regex = re.compile(pattern)
        if any(regex.search(s) for s in target_strings):
            return True
    return False

SUSPICIOUS_KEYWORDS = ['curl', 'bash', 'nc', 'wget', 'sh', 'python', 'perl', 'ruby']

def is_suspicious_command(cmdline):
    """
    Checks if any suspicious keyword is in the command line
    """
    if not cmdline:
        return False, ''
    combined = ' '.join(cmdline) if isinstance(cmdline, list) else cmdline
    for kw in SUSPICIOUS_KEYWORDS:
        if kw in combined:
            reason = f"Contains suspicious keyword: '{kw}'"
            return True, reason
    return False, ''

def scan_process(pid):
    try:
        proc = psutil.Process(pid)
        info = {}
        info['pid'] = pid
        info['ppid'] = proc.ppid()
        info['user'] = proc.username()
        info['name'] = proc.name()
        info['cmdline'] = proc.cmdline()
        info['exe'] = proc.exe()
        info['cpu_percent'] = proc.cpu_percent(interval=0.1)
        info['memory_percent'] = proc.memory_percent()
        info['create_time'] = proc.create_time()
        # Deep info could include open files, connections, cwd, env, loaded modules etc.
        info['open_files'] = [f.path for f in proc.open_files()]
        info['connections'] = [c.raddr for c in proc.connections(kind='inet') if c.raddr]
        info['cwd'] = proc.cwd()
        try:
            info['environ'] = proc.environ()
        except Exception:
            info['environ'] = {}

        # Check whitelist first
        if is_whitelisted(info['cmdline'], info['exe']):
            info['suspicious'] = False
            info['reason'] = "Whitelisted known safe process"
        else:
            suspicious, reason = is_suspicious_command(info['cmdline'])
            info['suspicious'] = suspicious
            info['reason'] = reason if suspicious else "No suspicious keywords detected"

        return info

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def generate_html_report(procs_info):
    # Generate summary counts
    suspicious_count = sum(1 for p in procs_info if p and p['suspicious'])
    clean_count = sum(1 for p in procs_info if p and not p['suspicious'])

    rows = ""
    for proc in procs_info:
        if not proc:
            continue
        start = datetime.fromtimestamp(proc.get("create_time", 0)).strftime("%Y-%m-%d %H:%M:%S")
        reason = proc.get('reason', 'N/A')
        suspicious_mark = "⚠️ Suspicious" if proc['suspicious'] else "✅ Clean"

        # Short cmdline for summary, full in details
        cmdline_short = ' '.join(proc['cmdline'])[:60] + ("..." if len(' '.join(proc['cmdline'])) > 60 else "")
        cmdline_full = ' '.join(proc['cmdline'])

        rows += f"""
        <tr class="{'suspicious' if proc['suspicious'] else 'clean'}">
            <td><button class="details-toggle" onclick="toggleDetails(this)">▶</button></td>
            <td>{proc['pid']}</td>
            <td>{proc['user']}</td>
            <td>{proc['name']}</td>
            <td title="{cmdline_full}">{cmdline_short}</td>
            <td>{proc['cpu_percent']:.2f}%</td>
            <td>{proc['memory_percent']:.2f}%</td>
            <td>{start}</td>
            <td>{suspicious_mark}</td>
        </tr>
        <tr class="details-row" style="display:none;">
            <td colspan="9">
                <strong>Reason Flagged:</strong> {reason}<br>
                <strong>Parent PID:</strong> {proc['ppid']}<br>
                <strong>Executable Path:</strong> {proc['exe']}<br>
                <strong>Current Working Directory:</strong> {proc['cwd']}<br>
                <strong>Open Files:</strong> {', '.join(proc['open_files']) if proc['open_files'] else 'None'}<br>
                <strong>Network Connections:</strong> {', '.join(str(c) for c in proc['connections']) if proc['connections'] else 'None'}<br>
                <strong>Environment Variables:</strong> {', '.join(f"{k}={v}" for k,v in proc['environ'].items()) if proc['environ'] else 'None'}<br>
            </td>
        </tr>
        """

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>Persistence Scanner Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 6px; max-width: 250px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }}
            th {{ background-color: #f4f4f4; cursor: pointer; }}
            tr.suspicious {{ background-color: #ffe6e6; }}
            tr.clean {{ background-color: #e6ffe6; }}
            .details-row td {{ background-color: #f9f9f9; font-size: 0.9em; }}
            button.details-toggle {{ cursor: pointer; background: none; border: none; font-size: 16px; }}
            #summary {{ margin-bottom: 10px; }}
            #filterSuspicious {{ margin-left: 20px; }}
        </style>
        <script>
            function toggleDetails(btn) {{
                var tr = btn.parentNode.parentNode;
                var detailsRow = tr.nextElementSibling;
                if (detailsRow.style.display === 'table-row') {{
                    detailsRow.style.display = 'none';
                    btn.textContent = '▶';
                }} else {{
                    detailsRow.style.display = 'table-row';
                    btn.textContent = '▼';
                }}
            }}

            function sortTable(n) {{
                var table = document.getElementById("procTable");
                var rows = Array.from(table.rows).slice(1); // exclude header
                var switching = true;
                var dir = "asc";
                var switchcount = 0;
                while (switching) {{
                    switching = false;
                    for (var i = 0; i < rows.length - 2; i += 2) {{
                        var x = rows[i].cells[n].textContent.toLowerCase();
                        var y = rows[i + 2].cells[n].textContent.toLowerCase();
                        if ((dir === "asc" && x > y) || (dir === "desc" && x < y)) {{
                            table.tBodies[0].insertBefore(rows[i + 2], rows[i]);
                            // Also swap the corresponding details row
                            table.tBodies[0].insertBefore(rows[i + 3], rows[i + 1]);
                            switching = true;
                            switchcount++;
                            break;
                        }}
                    }}
                    if (switchcount === 0 && dir === "asc") {{
                        dir = "desc";
                        switching = true;
                    }}
                }}
            }}

            function filterSuspicious() {{
                var table = document.getElementById("procTable");
                var checkbox = document.getElementById("showSuspiciousOnly");
                var rows = table.tBodies[0].rows;
                for (var i = 0; i < rows.length; i += 2) {{
                    var suspicious = rows[i].classList.contains('suspicious');
                    if (checkbox.checked && !suspicious) {{
                        rows[i].style.display = 'none';
                        rows[i + 1].style.display = 'none';
                    }} else {{
                        rows[i].style.display = '';
                        rows[i + 1].style.display = 'none'; // details hidden by default
                        // Reset toggle button icon to ▶
                        rows[i].querySelector("button.details-toggle").textContent = "▶";
                    }}
                }}
            }}
        </script>
    </head>
    <body>
        <h1>Persistence Scanner Report</h1>
        <div id="summary">
            Suspicious: {suspicious_count} | Clean: {clean_count}
            <label id="filterSuspicious"><input type="checkbox" id="showSuspiciousOnly" onchange="filterSuspicious()"> Show only suspicious</label>
        </div>
        <table id="procTable">
            <thead>
                <tr>
                    <th></th>
                    <th onclick="sortTable(1)">PID</th>
                    <th onclick="sortTable(2)">User</th>
                    <th onclick="sortTable(3)">Name</th>
                    <th onclick="sortTable(4)">Command Line</th>
                    <th onclick="sortTable(5)">CPU %</th>
                    <th onclick="sortTable(6)">Memory %</th>
                    <th onclick="sortTable(7)">Start Time</th>
                    <th onclick="sortTable(8)">Status</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </body>
    </html>
    """
    return html_template

def main():
    pids = psutil.pids()
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(scan_process, pid) for pid in pids]
        results = [f.result() for f in concurrent.futures.as_completed(futures) if f.result()]

    report_html = generate_html_report(results)
    with open("persistence_report.html", "w") as f:
        f.write(report_html)
    print("Report generated: persistence_report.html")

if __name__ == "__main__":
    main()
