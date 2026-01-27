import os
import re
import subprocess
from pathlib import Path

# Known suspicious patterns to look for in persistence items (example regex)
SUSPICIOUS_PATTERNS = [
    re.compile(r'curl\s+http', re.I),
    re.compile(r'wget\s+http', re.I),
    re.compile(r'python3?\s+-c', re.I),
    re.compile(r'osascript\s+-e', re.I),
    re.compile(r'launchctl\s+load', re.I),
    re.compile(r'base64\s+-d', re.I),
    re.compile(r'perl\s+-e', re.I),
]

# Known cloud storage folders to exclude from persistence scanning
CLOUD_STORAGE_FOLDERS = [
    "Box", "Box-Box",
    "OneDrive", "OneDrive - Personal", "OneDrive - Company",
    "Creative Cloud Files",
    "Dropbox",
    "com~apple~CloudDocs",
    "Google Drive"
]

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout.strip()
    except Exception as e:
        return f"Error running command '{cmd}': {e}"

def is_in_cloud_storage(path):
    """Return True if path is inside a known cloud storage folder."""
    home = str(Path.home())
    try:
        p = Path(path).resolve()
    except Exception:
        return False
    parts = p.parts

    # Check if the path is inside home directory and contains a cloud folder name
    if home in p.as_posix():
        for cloud_name in CLOUD_STORAGE_FOLDERS:
            # Check for path segments matching cloud storage folder names
            if cloud_name in parts:
                # Ensure the cloud storage folder is under home or Library/CloudStorage
                cloud_storage_dir = Path(home) / "Library" / "CloudStorage"
                if cloud_storage_dir in p.parents or str(Path(home) / cloud_name) in p.parents or str(Path(home) / cloud_name) == p.as_posix():
                    return True
                # Also directly under home folder
                if parts.index(cloud_name) > parts.index(Path.home().parts[-1]):
                    return True
    return False

def scan_directory_for_suspicious_files(directory, sudo=False):
    """
    Scan the given directory for suspicious files matching known patterns.
    Returns a list of suspicious files or empty if none found.
    Skips scanning cloud storage directories.
    """
    if is_in_cloud_storage(directory):
        return [], f"Skipped cloud storage folder: {directory}"

    if sudo:
        cmd = f"sudo ls '{directory}'"
    else:
        cmd = f"ls '{directory}'"
    output = run_cmd(cmd)
    if output.startswith("Error"):
        return [], output

    suspicious_files = []
    for line in output.splitlines():
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern.search(line):
                suspicious_files.append(line)
    return suspicious_files, None

def gather_launch_daemons():
    launch_daemons_paths = [
        "/Library/LaunchDaemons/",
        "/System/Library/LaunchDaemons/"
    ]
    all_suspicious = []
    for path in launch_daemons_paths:
        suspicious, err = scan_directory_for_suspicious_files(path, sudo=True)
        if err:
            all_suspicious.append(f"Could not scan {path}: {err}")
        else:
            for item in suspicious:
                all_suspicious.append(f"LaunchDaemon: {path}{item}")
    return all_suspicious

def gather_launch_agents():
    launch_agents_paths = [
        str(Path.home() / "Library" / "LaunchAgents"),
        "/Library/LaunchAgents/"
    ]
    all_suspicious = []
    for path in launch_agents_paths:
        suspicious, err = scan_directory_for_suspicious_files(path)
        if err:
            all_suspicious.append(f"Could not scan {path}: {err}")
        else:
            for item in suspicious:
                all_suspicious.append(f"LaunchAgent: {path}{item}")
    return all_suspicious

def gather_cron_jobs():
    cron_suspicious = []
    # Check user crontab
    user_cron = run_cmd("crontab -l")
    if user_cron and not user_cron.lower().startswith("no crontab"):
        for line in user_cron.splitlines():
            for pattern in SUSPICIOUS_PATTERNS:
                if pattern.search(line):
                    cron_suspicious.append(f"User cron job: {line}")
    # System crontabs and cron dirs to check
    system_cron_files = [
        "/etc/crontab",
        "/etc/cron.d/",
        "/etc/cron.daily/",
        "/etc/cron.hourly/",
        "/etc/cron.monthly/",
        "/etc/cron.weekly/",
    ]
    for file_path in system_cron_files:
        if os.path.exists(file_path):
            try:
                if os.path.isdir(file_path):
                    # Read each file inside directory
                    for fname in os.listdir(file_path):
                        full_path = os.path.join(file_path, fname)
                        with open(full_path, 'r') as f:
                            content = f.read()
                            for pattern in SUSPICIOUS_PATTERNS:
                                if pattern.search(content):
                                    cron_suspicious.append(f"System cron job file: {full_path}")
                else:
                    # It's a file
                    with open(file_path, 'r') as f:
                        content = f.read()
                        for pattern in SUSPICIOUS_PATTERNS:
                            if pattern.search(content):
                                cron_suspicious.append(f"System cron job file: {file_path}")
            except Exception as e:
                cron_suspicious.append(f"Could not read {file_path}: {e}")
    return cron_suspicious

def gather_suspicious_processes():
    suspicious_procs = []
    output = run_cmd("ps aux")
    if output.startswith("Error"):
        return [output]
    for line in output.splitlines():
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern.search(line):
                suspicious_procs.append(f"Suspicious process: {line}")
    return suspicious_procs

def main():
    report = {}

    report["LaunchDaemons"] = gather_launch_daemons()
    report["LaunchAgents"] = gather_launch_agents()
    report["CronJobs"] = gather_cron_jobs()
    report["SuspiciousProcesses"] = gather_suspicious_processes()

    return report

if __name__ == "__main__":
    import json
    results = main()
    print(json.dumps(results, indent=2))
