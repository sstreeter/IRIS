from typing import Any, Dict, List, Optional, Tuple
import sys
import re
import os
import plistlib
import datetime
import json

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers

def get_app_details(process_line: str) -> Dict[str, str]:
    """
    Extracts application details (Path, Version, Last Modified) from a process line.
    Attempts to identify the parenting .app bundle.
    """
    details = {
        "path": "Unknown",
        "version": "Unknown",
        "last_modified": "Unknown"
    }
    
    # Try to find an absolute path in the process line
    parts = process_line.split()
    candidate_path = None
    
    for part in parts:
        if part.startswith("/"):
            candidate_path = part
            break
            
    if not candidate_path:
        return details

    # Attempt to resolve the .app bundle path
    app_bundle_match = re.search(r"^(.+\.app)", candidate_path)
    if app_bundle_match:
        app_path = app_bundle_match.group(1)
        details["path"] = app_path
        
        # Get Last Modified Time
        try:
            mtime = os.path.getmtime(app_path)
            details["last_modified"] = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass 

        # Get Version from Info.plist
        info_plist_path = os.path.join(app_path, "Contents", "Info.plist")
        if os.path.exists(info_plist_path):
            try:
                with open(info_plist_path, "rb") as f:
                    plist_data = plistlib.load(f)
                    short_ver = plist_data.get("CFBundleShortVersionString")
                    bundle_ver = plist_data.get("CFBundleVersion")
                    
                    if short_ver and bundle_ver:
                        details["version"] = f"{short_ver} ({bundle_ver})"
                    elif short_ver:
                        details["version"] = short_ver
                    elif bundle_ver:
                        details["version"] = bundle_ver
            except Exception:
                pass
    else:
        details["path"] = candidate_path
        
    return details

def check_microsoft_defender(helpers: Any, app_instance: Any) -> Optional[Dict[str, str]]:
    """
    Checks Microsoft Defender status using 'mdatp health'.
    """
    try:
        # Check if mdatp is installed/runnable
        output = helpers.run_command("mdatp health --field app_version", check_shell=True, app_instance=app_instance)
        if not output or "command not found" in output:
            return None

        # Gather details
        version = output.strip().replace('"', '')
        
        real_time = helpers.run_command("mdatp health --field real_time_protection_enabled", check_shell=True, app_instance=app_instance).strip()
        real_time_enabled = "true" in real_time.lower()
        real_time_status = "Enabled" if real_time_enabled else "Disabled"
        
        defs_updated = helpers.run_command("mdatp health --field definitions_updated", check_shell=True, app_instance=app_instance).strip()
        
        path = "/Applications/Microsoft Defender.app"
        
        status_html = f"<span style='color: {'green' if real_time_enabled else 'red'}; font-weight: bold;'>{real_time_status}</span>"
        if real_time_enabled:
            status_html += " (Real-time Protection)"
            
        # Determine Severity & Remediation
        severity = "Safe"
        remediation = "None required."
        
        if not real_time_enabled:
            severity = "Critical"
            remediation = "Enable Real-time Protection immediately.<br>Use: <code>mdatp config real-time-protection --value enabled</code>"
        
        return {
            "vendor": "Microsoft Defender",
            "status": status_html,
            "path": path,
            "version": version,
            "last_modified": defs_updated,
            "severity": severity,
            "remediation": remediation
        }
    except Exception as e:
        app_instance.log_output(f"Error checking Microsoft Defender: {e}")
        return None

def check_xprotect(helpers: Any, app_instance: Any) -> Optional[Dict[str, str]]:
    """
    Checks XProtect status by verifying MobileAssets and background update settings.
    """
    try:
        # 1. Check for MobileAssets (modern source of truth)
        # Suppress errors if path not found (e.g. older macOS or restricted permissions)
        try:
            assets_output = helpers.run_command("ls /Library/Apple/System/Library/AssetsV2/", check_shell=True, app_instance=app_instance)
            has_assets = "MobileAsset_XProtect" in assets_output
        except Exception:
            has_assets = False
            assets_output = ""
        
        # 2. Check background updates
        try:
            bg_updates_output = helpers.run_command("defaults read /Library/Preferences/com.apple.SoftwareUpdate AutomaticallyInstallSystemData", check_shell=True, app_instance=app_instance)
            bg_updates_enabled = "1" in bg_updates_output.strip()
        except Exception:
            bg_updates_enabled = False

        status_msg = "Active"
        status_color = "green"
        severity = "Safe"
        remediation = "None required."
        
        details = []
        if has_assets:
            details.append("Signatures Present")
        else:
            details.append("Missing Signatures")
            status_color = "red"
            status_msg = "Issues Found"
            severity = "High"
            remediation = "Run macOS Software Update to restore XProtect assets."

        if bg_updates_enabled:
            details.append("Auto-Updates On")
        else:
            details.append("Auto-Updates Off")
            if severity == "Safe": # Only downgrade to Warning if not already High
                status_color = "orange"
                status_msg = "Config Warning"
                severity = "Medium"
                remediation = "Enable 'Install Security Responses and system files' in System Settings."

        status_html = f"<span style='color: {status_color}; font-weight: bold;'>{status_msg}</span>"
        if details:
            status_html += f" <br><span style='font-size: 0.8em'>({' | '.join(details)})</span>"

        # Try to get version from the app if it exists, though assets are the real definitions
        version = "Unknown"
        xprotect_path = "/Library/Apple/System/Library/CoreServices/XProtect.app"
        info_plist_path = os.path.join(xprotect_path, "Contents", "Info.plist")
        
        if os.path.exists(info_plist_path):
             try:
                with open(info_plist_path, "rb") as f:
                    plist_data = plistlib.load(f)
                    version = plist_data.get("CFBundleShortVersionString", "Unknown")
             except:
                 pass

        return {
            "vendor": "XProtect (macOS Native)",
            "status": status_html,
            "path": xprotect_path,
            "version": version,
            "last_modified": "Managed by macOS",
            "severity": severity,
            "remediation": remediation
        }

    except Exception as e:
        # Log purely for debugging, don't return dictionary so we might fall back or just show nothing specific
        # Actually returning a "Unknown" record is better than silence if we expected it to be there.
        return {
            "vendor": "XProtect (macOS Native)",
            "status": "<span style='color: gray;'>Unknown</span>",
            "path": "Unknown",
            "version": "Unknown",
            "last_modified": "Unknown",
            "severity": "Info",
            "remediation": "Could not verify XProtect status (Path/Permission issue)."
        }


def generate_antivirus_status_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Generates a report for antivirus status based on running processes and system checks."""
    app_instance.log_output("\n--- Generating Antivirus Status Report ---")
    
    detected_avs = []
    
    # 1. Run Specialized Checks
    
    # Microsoft Defender
    defender_data = check_microsoft_defender(helpers, app_instance)
    if defender_data:
        detected_avs.append(defender_data)
        
    # XProtect
    xprotect_data = check_xprotect(helpers, app_instance)
    if xprotect_data:
        detected_avs.append(xprotect_data)

    # 2. Process Scan for others
    
    # Known AV Vendors and their process keywords
    known_av_vendors: Dict[str, List[str]] = {
        "CrowdStrike Falcon": ["Falcon", "com.crowdstrike."],
        "SentinelOne": ["sentinel", "com.sentinelone."],
        "Carbon Black": ["cbdaemon", "com.carbonblack."],
        # Defender and XProtect handled above, but kept here as fallback words if specialized checks fail unexpectedly
        "Sophos": ["Sophos", "com.sophos."],
        "McAfee": ["McAfee", "VShield", "com.mcafee."],
        "Symantec / Norton": ["Symantec", "Norton", "com.symantec."],
        "Malwarebytes": ["Malwarebytes", "com.malwarebytes."],
        "ESET": ["esets_daemon", "esets_gui", "com.eset."],
        "Bitdefender": ["Bitdefender", "com.bitdefender."],
        "Little Snitch": ["Little Snitch", "com.obdev.littlesnitch"],
        "LuLu": ["LuLu", "com.objective-see.lulu"],
        "Jamf Protect": ["JamfProtect"],
        "Cylance": ["Cylance"],
        "Webroot": ["Webroot", "WRSVC"],
        "Trend Micro": ["Trend", "iCoreService"],
        "Avast": ["Avast", "com.avast."],
        "Kaspersky": ["kav", "kaspersky"],
    }
    
    already_detected_vendors = [d['vendor'] for d in detected_avs]
    # Map friendly names to keys if needed, but for now simple exclusion works

    processes_output = ""
    if sys.platform == "win32":
        processes_output = helpers.run_command(r"powershell.exe -Command \"Get-Process | Select-Object -ExpandProperty ProcessName\"", app_instance=app_instance)
    else:
        processes_output = helpers.run_command("ps aux", check_shell=True, app_instance=app_instance)

    if processes_output:
        lines = processes_output.splitlines()
        
        for vendor, keywords in known_av_vendors.items():
            # Skip if already detected via specialized check
            # Note: "Microsoft Defender" vs "Microsoft Defender" key - simple string matching
            if vendor in already_detected_vendors:
                continue
            
            found_this_vendor = False
            for keyword in keywords:
                if found_this_vendor: break
                
                for line in lines:
                    if keyword.lower() in line.lower():
                        details = get_app_details(line)
                        detected_avs.append({
                            "vendor": vendor,
                            "status": "<span style='color: green; font-weight: bold;'>Running</span>",
                            "path": details["path"],
                            "version": details["version"],
                            "last_modified": details["last_modified"],
                            "severity": "Safe",
                            "remediation": "None required."
                        })
                        found_this_vendor = True
                        break

    # Build HTML
    html_body = "<h2>Antivirus Status</h2>"
    
    # CSS for table wrapping and badges
    html_body += """
    <style>
        .av-table { width: 100%; border-collapse: collapse; }
        .av-table th, .av-table td { padding: 8px; border: 1px solid #ddd; text-align: left; vertical-align: top; }
        .av-table th { background-color: #f2f2f2; }
        .path-col { word-break: break-all; max-width: 250px; font-size: 0.9em; }
        .badge { padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; font-size: 0.85em; display: inline-block; }
        .badge-critical { background-color: #dc3545; }
        .badge-high { background-color: #fd7e14; }
        .badge-medium { background-color: #ffc107; color: #212529; }
        .badge-safe { background-color: #28a745; }
        .badge-info { background-color: #17a2b8; }
    </style>
    """
    
    if detected_avs:
        html_body += "<p>The following security software was detected on the system:</p>"
        html_body += "<table class='av-table'>"
        html_body += "<thead><tr><th>Severity</th><th>Security Software</th><th>Status</th><th>Remediation</th><th>Version</th><th class='path-col'>Path</th><th>Last Updated</th></tr></thead>"
        html_body += "<tbody>"
        for av in detected_avs:
            sev = av['severity']
            badge_class = f"badge-{sev.lower()}" if sev.lower() in ["critical", "high", "medium", "safe", "info"] else "badge-info"
            
            html_body += f"<tr>"
            html_body += f"<td><span class='badge {badge_class}'>{sev.upper()}</span></td>"
            html_body += f"<td><strong>{av['vendor']}</strong></td>"
            html_body += f"<td>{av['status']}</td>"
            html_body += f"<td>{av['remediation']}</td>"
            html_body += f"<td>{av['version']}</td>"
            html_body += f"<td class='path-col'>{av['path']}</td>"
            html_body += f"<td>{av['last_modified']}</td>"
            html_body += f"</tr>"
        html_body += "</tbody>"
        html_body += "</table>"
    else:
        html_body += "<div style='display: flex; align-items: center; background-color: #fff3cd; color: #856404; padding: 15px; border: 1px solid #ffeeba; border-radius: 4px;'>"
        html_body += "<span style='font-size: 24px; margin-right: 15px;'>⚠️</span>"
        html_body += "<div><strong>No common third-party Antivirus/EDR processes were detected.</strong><br>"
        html_body += "Note: This check looks for running processes of known vendors. It is possible the software is using a different process name or is hidden.</div>"
        html_body += "</div>"

    html_body += "<h3>Methodology</h3>"
    html_body += "<ul>"
    html_body += "<li><strong>Microsoft Defender:</strong> Verified using <code>mdatp health</code> CLI for real-time status and definition updates. checks specifically for enabled real-time protection.</li>"
    html_body += "<li><strong>XProtect:</strong> Verified via system mobile assets (signatures) and background update configuration.</li>"
    html_body += "<li><strong>Other Vendors:</strong> Detected by scanning running processes and inspecting application bundles for version headers.</li>"
    html_body += "</ul>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Antivirus_Status_Report.html", 
        "Antivirus Status Report", 
        html_body,
        browser_preference=browser_preference
    )
