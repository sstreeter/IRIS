#!/usr/bin/env python3

import os
import subprocess
import plistlib
import json
import argparse
import concurrent.futures
from datetime import datetime
from html import escape

# Whitelist common system and known safe paths
WHITELISTED_PATH_PREFIXES = [
    "/System/Library/",
    "/usr/lib/",
    "/usr/bin/",
    "/bin/",
    "/sbin/",
    "/Library/Application Support/Logitech",
    "/Applications/Adobe",
    "/Applications/Google Chrome.app",
    "/Applications/Visual Studio Code.app",
]

# Suspicious keyword indicators
SUSPICIOUS_KEYWORDS = [
    "curl", "wget", "nc", "base64", "eval", "osascript",
    "python", "perl", "ruby", "socat", "launchctl",
    "crypt", "reverse", "malicious", "payload", "exec", "sh", "http"
]

# Directories to scan for persistence mechanisms
PERSISTENCE_DIRS = {
    "LaunchAgents": [
        os.path.expanduser("~/Library/LaunchAgents"),
        "/Library/LaunchAgents"
    ],
    "LaunchDaemons": [
        "/Library/LaunchDaemons",
        "/System/Library/LaunchDaemons"
    ]
}

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Fast macOS Persistence Scanner with optional HTML output"
    )
    parser.add_argument("--verbose", action="store_true", help="Show skipped files and file counts")
    parser.add_argument("--exhaustive", action="store_true", help="Include whitelisted paths in scan")
    parser.add_argument("--html", action="store_true", help="Generate an HTML report")
    return parser.parse_args()

def is_whitelisted(path, exhaustive=False):
    if exhaustive:
        return False
    return any(path.startswith(prefix) for prefix in WHITELISTED_PATH_PREFIXES)

def list_files(directory):
    try:
        return [os.path.join(directory, f) for f in os.listdir(directory)]
    except Exception:
        return []

def scan_plist_for_keywords(plist_path):
    try:
        with open(plist_path, 'rb') as f:
            data = plistlib.load(f)
        suspicious = []
        for key, val in data.items():
            texts = []
            if isinstance(val, str):
                texts = [val]
            elif isinstance(val, list):
                texts = [item for item in val if isinstance(item, str)]
            for text in texts:
                for keyword in SUSPICIOUS_KEYWORDS:
                    if keyword in text:
                        suspicious.append((key, text))
        return suspicious if suspicious else None
    except Exception:
        return None

def scan_launch_items(item_type, paths, exhaustive=False, verbose=False):
    results = []
    skipped = []
    for path in paths:
        if not os.path.exists(path):
            continue
        files = list_files(path)
        for f in files:
            if not f.endswith(".plist"):
                continue
            if is_whitelisted(f, exhaustive):
                if verbose:
                    skipped.append(f)
                continue
            suspicious = scan_plist_for_keywords(f)
            if suspicious:
                results.append({
                    "file": f,
                    "matches": suspicious
                })
            elif verbose:
                skipped.append(f)
    return item_type, results, skipped

def scan_cron_jobs():
    try:
        output = subprocess.check_output(["crontab", "-l"], stderr=subprocess.DEVNULL).decode()
        return [line for line in output.splitlines() if any(k in line for k in SUSPICIOUS_KEYWORDS)]
    except Exception:
        return []

def scan_processes(exhaustive=False):
    suspicious = []
    try:
        output = subprocess.check_output(["ps", "aux"]).decode()
        for line in output.splitlines():
            lower_line = line.lower()
            if not exhaustive and any(path.lower() in lower_line for path in WHITELISTED_PATH_PREFIXES):
                continue
            if any(k in lower_line for k in SUSPICIOUS_KEYWORDS):
                suspicious.append(line)
    except Exception:
        pass
    return suspicious

def generate_html_report(results, filename="macos_persistence_scan_report.html"):
    html = f"""<html>
<head><title>macOS Persistence Scan</title>
<style>
body {{ font-family: monospace; background: #f7f7f7; padding: 1em; }}
h1, h2 {{ color: #333; }}
code {{ background: #eee; padding: 2px 4px; border-radius: 4px; }}
</style>
</head><body>
<h1>macOS Persistence Scan Report</h1>
<p><b>Generated:</b> {datetime.now()}</p>
"""

    for section, items in results.items():
        html += f"<h2>{escape(section)}</h2><ul>"
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    html += f"<li><b>{escape(item['file'])}</b><ul>"
                    for k, v in item["matches"]:
                        html += f"<li>{escape(k)} → <code>{escape(v)}</code></li>"
                    html += "</ul></li>"
                else:
                    html += f"<li><code>{escape(str(item))}</code></li>"
        elif isinstance(items, dict):  # Skipped files
            for category, skipped in items.items():
                html += f"<li><b>{category}</b>: {len(skipped)} skipped</li>"
        html += "</ul>"
    html += "</body></html>"

    with open(filename, "w") as f:
        f.write(html)
    print(f"✅ HTML report saved to {filename}")

def main():
    args = parse_arguments()

    results = {
        "LaunchAgents": [],
        "LaunchDaemons": [],
        "CronJobs": [],
        "SuspiciousProcesses": [],
    }

    if args.verbose:
        results["SkippedFiles"] = {}

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for k, v in PERSISTENCE_DIRS.items():
            futures.append(executor.submit(scan_launch_items, k, v, args.exhaustive, args.verbose))
        for future in concurrent.futures.as_completed(futures):
            item_type, items, skipped = future.result()
            results[item_type].extend(items)
            if args.verbose:
                results["SkippedFiles"][item_type] = skipped

        cron_fut = executor.submit(scan_cron_jobs)
        proc_fut = executor.submit(scan_processes, args.exhaustive)
        results["CronJobs"] = cron_fut.result()
        results["SuspiciousProcesses"] = proc_fut.result()

    if args.html:
        generate_html_report(results)
    else:
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
