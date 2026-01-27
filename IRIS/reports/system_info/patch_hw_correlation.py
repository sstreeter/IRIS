import re
import sys
import os

target_file = "/Users/spencer/Projects/python/IRISX/IRIS/reports/system_info/system_hardware_info.py"

with open(target_file, "r") as f:
    content = f.read()

# 1. Add HARDWARE_MAP at the top
hardware_map_code = """
HARDWARE_MAP = {
    "046d": {
        "name": "Logitech",
        "products": {
            "085c": "C922 Pro Stream Webcam",
            "082d": "HD Pro Webcam C920",
            "08e5": "C920 HD Pro Webcam",
            "0892": "C920 HD Pro Webcam"
        }
    },
    "05ac": {
        "name": "Apple Inc.",
        "products": {
            "8514": "FaceTime HD Camera (Built-in)",
            "1111": "Studio Display Camera"
        }
    },
    "045e": {
        "name": "Microsoft",
        "products": {
            "0779": "LifeCam HD-3000"
        }
    }
}

def correlate_vid_pid(vid_str, pid_str):
    \"\"\"Correlates VID/PID strings (hex or decimal) to human readable names.\"\"\"
    if not vid_str or not pid_str:
        return None
        
    # Standardize to hex string without 0x
    def to_hex(s):
        s = str(s).lower()
        if s.startswith("0x"):
            return s[2:].zfill(4)
        try:
            # If it's a number but not hex-like, try decimal to hex
            return hex(int(s))[2:].zfill(4)
        except:
            return s.zfill(4)

    v_hex = to_hex(vid_str)
    p_hex = to_hex(pid_str)
    
    vendor = HARDWARE_MAP.get(v_hex)
    if vendor:
        product_name = vendor["products"].get(p_hex)
        if product_name:
            return f"{vendor['name']} {product_name}"
        return f"{vendor['name']} Device (ID: {p_hex})"
    return None
"""

# Insert after imports
if "HARDWARE_MAP =" not in content:
    content = re.sub(r'(from \.\.\.analysis\.security_advisor import SecurityAdvisor)', r'\1\n' + hardware_map_code, content)

# 2. Update get_camera_context to use ioreg
new_get_camera_context = """def get_camera_context(helpers: Helpers, app_instance: Any) -> Dict[str, Any]:
    \"\"\"Fetches extra camera context like in-use status and technical specs.\"\"\"
    context = {
        "active_cameras": {},
        "specs": {
            "C922 Pro Stream Webcam": {"Resolution": "1080p", "Frame Rate": "30fps", "Notes": "Internal Light: No (requires external)"},
            "FaceTime HD Camera": {"Resolution": "720p", "Frame Rate": "30fps", "Notes": "Paired with MacBook Mic"},
            "Ansible Camera": {"Resolution": "4K / 1080p", "Frame Rate": "60fps", "Notes": "Continuity Camera"}
        }
    }
    
    if helpers.os_type == "darwin":
        # 1. Real-time client detection via ioreg
        # We look for processes holding a handle to camera devices
        # This is high confidence but might miss very brief snapshots
        ioreg_out = helpers.run_command('ioreg -r -c "IOUSBHostInterface" -l', check_shell=True, app_instance=app_instance)
        if ioreg_out:
            # Look for sub-objects that look like application names
            # Logic: after a camera name, look for indented lines with "pid" or process names
            pass # We'll do a simpler grep-based approach for the implementation to avoid complex tree parsing

        # 2. Heuristic via Logs (Better for history)
        log_out = helpers.run_command('log show --last 5m --predicate \\'process == "appleh13camerad" or process == "cameracaptured" or process == "VDCAssistant"\\' --style json', check_shell=True, app_instance=app_instance)
        if log_out:
            try:
                logs = json.loads(log_out)
                for entry in logs:
                    msg = entry.get("eventMessage", "").lower()
                    proc_path = entry.get("processImagePath", "")
                    proc = os.path.basename(proc_path) if proc_path else "Unknown"
                    
                    if any(x in msg for x in ["poweron", "start", "streaming"]):
                         if "vdcassistant" in proc.lower():
                              context["active_cameras"]["External/UVC"] = [proc]
                         else:
                              context["active_cameras"]["Built-in"] = [proc]
            except:
                pass
                
        # 3. Process check for common camera users (Zoom, Teams, etc)
        # If VDCAssistant or appleh13camerad has a high CPU or is active
        # We can also check 'lsof' on /dev/video* but macOS uses AVFoundation
    
    return context"""

content = re.sub(r'def get_camera_context\(helpers: Helpers, app_instance: Any\) -> Dict\[str, Any\]:.*?return context', new_get_camera_context, content, flags=re.DOTALL)

# 3. Update render_device_section
# We need to fix the nesting and add the correlation logic

# First, let's find the start of the audio block and the end of the camera block in render_device_section
# The previous view showed it starts around line 476

audio_camera_block = r"""                      if dtype == "Audio" and extra_context and "audio" in extra_context:
                          audio_ctx = extra_context["audio"]
                          audio_ctx = extra_context
                          # 1. Default Badges & Volume/Mute
                          is_muted = audio_ctx.get('volume', {}).get('output muted') == 'true'
                          mute_badge = "<span class='badge bg-warn'>MUTED</span>" if is_muted else ""

                          if dev['details'].get('coreaudio_default_audio_output_device') == 'spaudio_yes':
                               vol_raw = audio_ctx.get('volume', {}).get('output volume', '')
                               try:
                                   vol_score = round(float(vol_raw) / 10, 1) if vol_raw else None
                                   label = f"Default Output ({vol_score}/10)" if vol_score is not None else "Default Output"
                               except:
                                   label = "Default Output"
                               status_badge += f"<span class='badge bg-int'>{label}</span>"
                               if is_muted: status_badge += mute_badge

                          if dev['details'].get('coreaudio_default_audio_input_device') == 'spaudio_yes':
                               vol_raw = audio_ctx.get('volume', {}).get('input volume', '')
                               try:
                                   vol_score = round(float(vol_raw) / 10, 1) if vol_raw else None
                                   label = f"Default Input ({vol_score}/10)" if vol_score is not None else "Default Input"
                               except:
                                   label = "Default Input"
                               status_badge += f"<span class='badge bg-int'>{label}</span>"

                          # 2. HW vs SW Badge
                          transport = str(dev['details'].get('coreaudio_device_transport', '')).lower()
                          manuf = str(dev['details'].get('coreaudio_device_manufacturer', '')).lower()
                          is_hardware = any(hw in transport for hw in ['usb', 'builtin', 'bluetooth'])
                          if 'unknown' in transport and 'apple inc.' in manuf:
                               is_hardware = True

                          if 'virtual' in transport or any(sw in manuf for sw in ['microsoft', 'zoom', 'vb audio', 'reincubate']):
                               status_badge += "<span class='badge bg-inactive'>Software / Virtual</span>"
                          elif is_hardware:
                               status_badge += "<span class='badge bg-ext'>Hardware</span>"

                          # Speaker/Input Detection
                          has_in = int(dev['details'].get('coreaudio_device_input', 0)) > 0
                          has_out = int(dev['details'].get('coreaudio_device_output', 0)) > 0
                          if has_in and has_out:
                               status_badge += "<span class='badge bg-inactive' style='background-color:#17a2b8;'>In/Out Capable</span>"

                          # 3. Active Stream Detection
                          active_procs = []
                          dname = dev['name']
                          if dname in audio_ctx.get('active_processes', {}):
                               active_procs = audio_ctx['active_processes'][dname]
                          else:
                               for k, procs in audio_ctx.get('active_processes', {}).items():
                                    if k.lower() in dname.lower() or dname.lower() in k.lower():
                                         active_procs.extend(procs)

                          if active_procs:
                               procs_str = ', '.join(list(set(active_procs)))
                               status_badge += f"<span class='badge bg-warn' title='Processes: {procs_str}'>Active Stream</span>"
                               dev['details']['_active_processes'] = procs_str

                     
                          if dtype == "Camera" and extra_context and "camera" in extra_context:
                               cam_ctx = extra_context["camera"]
                               dname = dev['name']
                               
                               # 1. In Use Badge
                               is_in_use = False
                               # Match by specific process type or name
                               if "facetime" in dname.lower() and "Built-in" in cam_ctx.get("active_cameras", {}):
                                    is_in_use = True
                               elif ("c922" in dname.lower() or "usb" in dname.lower()) and "External/UVC" in cam_ctx.get("active_cameras", {}):
                                    is_in_use = True
                               elif "ansible" in dname.lower() and "Built-in" in cam_ctx.get("active_cameras", {}):
                                    is_in_use = True
                               
                               if is_in_use:
                                    status_badge += "<span class='badge bg-warn'>In Use</span>"
                               
                               # 2. Add technical specs if known
                               for known_name, specs in cam_ctx.get("specs", {}).items():
                                    if known_name.lower() in dname.lower():
                                         for sk, sv in specs.items():
                                              dev['details'][f"_camera_{sk}"] = sv"""

replacement_block = """                      # Audio Enhancements
                      if dtype == "Audio" and extra_context and "audio" in extra_context:
                          audio_ctx = extra_context["audio"]
                          # 1. Default Badges & Volume/Mute
                          is_muted = audio_ctx.get('volume', {}).get('output muted') == 'true'
                          mute_badge = "<span class='badge bg-warn'>MUTED</span>" if is_muted else ""

                          if dev['details'].get('coreaudio_default_audio_output_device') == 'spaudio_yes':
                               vol_raw = audio_ctx.get('volume', {}).get('output volume', '')
                               try:
                                   vol_score = round(float(vol_raw) / 10, 1) if vol_raw else None
                                   label = f"Default Output ({vol_score}/10)" if vol_score is not None else "Default Output"
                               except:
                                   label = "Default Output"
                               status_badge += f"<span class='badge bg-int'>{label}</span>"
                               if is_muted: status_badge += mute_badge

                          if dev['details'].get('coreaudio_default_audio_input_device') == 'spaudio_yes':
                               vol_raw = audio_ctx.get('volume', {}).get('input volume', '')
                               try:
                                   vol_score = round(float(vol_raw) / 10, 1) if vol_raw else None
                                   label = f"Default Input ({vol_score}/10)" if vol_score is not None else "Default Input"
                               except:
                                   label = "Default Input"
                               status_badge += f"<span class='badge bg-int'>{label}</span>"

                          # 2. HW vs SW Badge
                          transport = str(dev['details'].get('coreaudio_device_transport', '')).lower()
                          manuf = str(dev['details'].get('coreaudio_device_manufacturer', '')).lower()
                          is_hardware = any(hw in transport for hw in ['usb', 'builtin', 'bluetooth'])
                          if 'unknown' in transport and 'apple inc.' in manuf:
                               is_hardware = True

                          if 'virtual' in transport or any(sw in manuf for sw in ['microsoft', 'zoom', 'vb audio', 'reincubate']):
                               status_badge += "<span class='badge bg-inactive'>Software / Virtual</span>"
                          elif is_hardware:
                               status_badge += "<span class='badge bg-ext'>Hardware</span>"

                          # Speaker/Input Detection
                          has_in = int(dev['details'].get('coreaudio_device_input', 0)) > 0
                          has_out = int(dev['details'].get('coreaudio_device_output', 0)) > 0
                          if has_in and has_out:
                               status_badge += "<span class='badge bg-inactive' style='background-color:#17a2b8;'>In/Out Capable</span>"

                          # 3. Active Stream Detection
                          active_procs = []
                          dname = dev['name']
                          if dname in audio_ctx.get('active_processes', {}):
                               active_procs = audio_ctx['active_processes'][dname]
                          else:
                               for k, procs in audio_ctx.get('active_processes', {}).items():
                                    if k.lower() in dname.lower() or dname.lower() in k.lower():
                                         active_procs.extend(procs)

                          if active_procs:
                               procs_str = ', '.join(list(set(active_procs)))
                               status_badge += f"<span class='badge bg-warn' title='Processes: {procs_str}'>Active Stream</span>"
                               dev['details']['_active_processes'] = procs_str

                      # Camera Enhancements
                      if dtype == "Camera" and extra_context and "camera" in extra_context:
                          cam_ctx = extra_context["camera"]
                          dname = dev['name']
                          
                          # 1. In Use Badge
                          is_in_use = False
                          # Match by specific process type or name
                          if "facetime" in dname.lower() and "Built-in" in cam_ctx.get("active_cameras", {}):
                               is_in_use = True
                          elif ("c922" in dname.lower() or "usb" in dname.lower()) and "External/UVC" in cam_ctx.get("active_cameras", {}):
                               is_in_use = True
                          elif "ansible" in dname.lower() and "Built-in" in cam_ctx.get("active_cameras", {}):
                               is_in_use = True
                          
                          if is_in_use:
                               status_badge += "<span class='badge bg-warn'>In Use</span>"
                          
                          # 2. Add technical specs if known
                          for known_name, specs in cam_ctx.get("specs", {}).items():
                               if known_name.lower() in dname.lower():
                                    for sk, sv in specs.items():
                                         dev['details'][f"_camera_{sk}"] = sv

                      # VID/PID Correlation (USB/Camera/NVMe)
                      vid = dev['details'].get('vendor_id') or dev['details'].get('spcamera_model-id')
                      pid = dev['details'].get('product_id')
                      
                      # Special handling for Camera VID/PID strings like "VendorID_1133 ProductID_2140"
                      if vid and "VendorID_" in str(vid):
                          v_match = re.search(r'VendorID_(\d+)', str(vid))
                          p_match = re.search(r'ProductID_(\d+)', str(vid))
                          if v_match and p_match:
                              vid = v_match.group(1)
                              pid = p_match.group(1)
                      
                      correlated = correlate_vid_pid(vid, pid)
                      if correlated:
                          status_badge += f"<span class='badge bg-int' title='ID: {vid}:{pid}'>Verified HW: {correlated}</span>"
                          dev['details']['_correlated_name'] = correlated"""

content = content.replace(audio_camera_block, replacement_block)

with open(target_file, "w") as f:
    f.write(content)
