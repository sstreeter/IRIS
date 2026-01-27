import os
import json
import subprocess
import glob
from datetime import datetime
from typing import Any, List, Dict
from ...helpers import Helpers, MockAppInstance

def get_quarantine_url(file_path: str) -> str:
    """
    Extracts the source URL from the com.apple.quarantine extended attribute.
    Format is typically: flags;date;agent;UUID;URL
    """
    try:
        # Use xattr -p to get the attribute
        # -r is not needed for specific file
        result = subprocess.run(
            ['xattr', '-p', 'com.apple.quarantine', file_path],
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            val = result.stdout.strip()
            # Split by semi-colon
            parts = val.split(';')
            if len(parts) >= 3:
                # The URL is generally the last item, or 3rd/4th depending on version
                # Often: 0081;5f22a...;Chrome;UUID;http://...
                for part in parts:
                    if part.startswith("http"):
                        return part
                # Fallback: if last part looks like domain/url
                return parts[-1]
    except Exception:
        pass
    return "N/A"

def get_chrome_extensions(app_instance: Any) -> List[Dict[str, str]]:
    extensions = []
    base_path = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Extensions")
    if os.path.exists(base_path):
        try:
            for ext_id in os.listdir(base_path):
                ext_dir = os.path.join(base_path, ext_id)
                if os.path.isdir(ext_dir):
                    # Usually there's a version subdirectory
                    versions = os.listdir(ext_dir)
                    if not versions: continue
                    # Pick latest version
                    latest_ver = sorted(versions)[-1]
                    manifest_path = os.path.join(ext_dir, latest_ver, "manifest.json")
                    
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                name = data.get('name', 'Unknown')
                                # Handle localized names (__MSG_...) logic slightly complex, skip for now
                                if name.startswith("__MSG_"):
                                    name = f"{name} (System/Local)"
                                extensions.append({
                                    "browser": "Chrome",
                                    "name": name,
                                    "version": data.get('version', 'N/A'),
                                    "id": ext_id
                                })
                        except: pass
        except Exception as e:
            app_instance.log_output(f"Error scanning Chrome extensions: {e}")
    return extensions

def get_firefox_extensions(app_instance: Any) -> List[Dict[str, str]]:
    extensions = []
    # Find default profile
    profiles_path = os.path.expanduser("~/Library/Application Support/Firefox/Profiles")
    if os.path.exists(profiles_path):
        try:
            for profile in os.listdir(profiles_path):
                if profile.endswith(".default") or profile.endswith(".default-release"):
                    ext_dir = os.path.join(profiles_path, profile, "extensions")
                    if os.path.isdir(ext_dir):
                        # List .xpi files or directories
                        for item in os.listdir(ext_dir):
                             extensions.append({
                                 "browser": "Firefox",
                                 "name": item, # Often ID or name
                                 "version": "N/A",
                                 "id": "See Name"
                             })
                    # Also check extensions.json for more detail?
                    # Keeping it simple for now.
        except Exception as e:
            app_instance.log_output(f"Error scanning Firefox extensions: {e}")
    return extensions

def get_safari_extensions(helpers: Helpers, app_instance: Any) -> List[Dict[str, str]]:
    extensions = []
    # Use pluginkit
    try:
        # pluginkit -m -p com.apple.Safari.extension
        out = helpers.run_command("pluginkit -m -p com.apple.Safari.extension", check_shell=True, app_instance=app_instance)
        if out:
            for line in out.splitlines():
                # Format: + com.vendor.plugin (1.0)
                # Cleaning it up
                line = line.strip()
                if not line: continue
                # Simple parse
                parts = line.split()
                if len(parts) >= 2:
                    ext_id = parts[1]
                    ver = parts[2] if len(parts) > 2 else "N/A"
                    extensions.append({
                        "browser": "Safari",
                        "name": ext_id,
                        "version": ver,
                        "id": ext_id
                    })
    except Exception as e:
        app_instance.log_output(f"Error scanning Safari extensions: {e}")
    return extensions

def get_recent_downloads(app_instance: Any = None) -> List[Dict[str, str]]:
    downloads = []
    down_dir = os.path.expanduser("~/Downloads")
    
    # Time Filter
    t_start = None
    t_end = None
    if app_instance:
        tr = getattr(app_instance, 'time_range', {})
        t_start = tr.get("start")
        t_end = tr.get("end")

    if os.path.exists(down_dir):
        try:
            # List files
            files = [os.path.join(down_dir, f) for f in os.listdir(down_dir) if not f.startswith('.')]
            # Sort by mtime
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            for f_path in files[:50]: # Scan top 50
                mtime_ts = os.path.getmtime(f_path)
                mtime_dt = datetime.fromtimestamp(mtime_ts)
                
                # Check Time Range
                if t_start and mtime_dt < t_start: continue
                if t_end and mtime_dt > t_end: continue

                fname = os.path.basename(f_path)
                mtime_str = mtime_dt.strftime("%Y-%m-%d %H:%M:%S")
                # Get Source URL
                source_url = get_quarantine_url(f_path)
                
                downloads.append({
                    "name": fname,
                    "date": mtime_str,
                    "source": source_url,
                    "path": f_path
                })
        except: pass
    return downloads

def generate_user_activity_report(app_instance: Any, helpers: Helpers, browser_preference: str = "System Default"):
    """
    Generates a report on User Activity:
    1. Recent Downloads (with Source URLs)
    2. Installed Browser Extensions
    """
    app_instance.log_output("\n--- Generating User Activity Report ---")
    
    html_body = "<h2>User Activity: Downloads & Extensions</h2>"
    
    # 1. Downloads
    downloads = get_recent_downloads(app_instance)
    html_body += "<h3>Recent Downloads (Last 20)</h3>"
    if downloads:
        html_body += "<table><thead><tr><th>Date</th><th>Filename</th><th>Source URL (Quarantine Data)</th></tr></thead><tbody>"
        for d in downloads:
            source_display = d['source']
            if len(source_display) > 60:
                source_display = source_display[:30] + "..." + source_display[-25:]
            
            html_body += f"<tr><td>{d['date']}</td><td>{d['name']}</td><td style='font-size:0.9em; color:#555;'>{source_display}</td></tr>"
        html_body += "</tbody></table>"
    else:
        html_body += "<p>No recent downloads found.</p>"
        
    # 2. Browser Extensions
    html_body += "<h3>Browser Extensions / Plugins</h3>"
    all_exts = []
    all_exts.extend(get_chrome_extensions(app_instance))
    all_exts.extend(get_firefox_extensions(app_instance))
    all_exts.extend(get_safari_extensions(helpers, app_instance))
    
    if all_exts:
        html_body += "<table><thead><tr><th>Browser</th><th>Name / ID</th><th>Version</th></tr></thead><tbody>"
        for ext in all_exts:
            html_body += f"<tr><td><strong>{ext['browser']}</strong></td><td>{ext['name']}<br/><small>{ext['id']}</small></td><td>{ext['version']}</td></tr>"
        html_body += "</tbody></table>"
    else:
        html_body += "<p>No browser extensions detected (Chrome/Firefox/Safari).</p>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "User_Activity_Report.html", 
        "User Activity Report", 
        html_body,
        browser_preference=browser_preference
    )
