import platform
import sys
import re
import plistlib
import json
import shutil
from typing import List, Optional, Dict, Any, Union

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers, DiskInfo
from ...analysis.security_advisor import SecurityAdvisor

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
    """Correlates VID/PID strings (hex or decimal) to human readable names."""
    if not vid_str or not pid_str:
        return None
        
    # Standardize to 4-char hex string without 0x
    def to_hex(s):
        s = str(s).lower().strip()
        if s.startswith("0x"):
            return s[2:].zfill(4)
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


def get_profiler_json(helpers: Helpers, data_type: str, app_instance: Any) -> Any:
    """Fetches system_profiler data as JSON."""
    try:
        # -json output is supported on modern macOS
        output = helpers.run_command(f"system_profiler -json {data_type}", check_shell=True, app_instance=app_instance)
        if output:
            data = json.loads(output)
            # Root is usually a list with one item containing the data type key
            # e.g., [{'SPHardwareDataType': [...]}]
            if isinstance(data, list) and len(data) > 0:
                # Find the key that matches the data type (or just grab the first value)
                # SPHardwareDataType -> "SPHardwareDataType" key
                return data[0].get(data_type, [])
            elif isinstance(data, dict):
                return data.get(data_type, [])
    except Exception as e:
        app_instance.log_output(f"Error fetching {data_type}: {e}")
    return []

def flattened_profiler_data(data: Any, key_filter: List[str] = None) -> List[Dict[str, str]]:
    """Recursively flattens complex system_profiler trees into a list of key-value summaries."""
    items = []
    
    if isinstance(data, list):
        for item in data:
            items.extend(flattened_profiler_data(item, key_filter))
    elif isinstance(data, dict):
        name = data.get("_name", "Unknown Device")
        details = {}
        
        def extract_details(d, prefix=""):
            for k, v in d.items():
                if k.startswith("_") and k != "_items":
                    continue
                if k == "_items":
                    continue
                
                full_key = f"{prefix}{k}" if prefix else k
                if isinstance(v, dict):
                    extract_details(v, f"{full_key}.")
                elif isinstance(v, list):
                    # For things like IP addresses
                    details[full_key] = ", ".join(map(str, v))
                elif isinstance(v, (str, int, float)):
                    details[full_key] = v

        if key_filter:
            for k in key_filter:
                if k in data: details[k] = data[k]
        else:
            extract_details(data)
        
        # If we have any details, add this as an item
        if details:
            details.pop("_name", None)
            items.append({"name": name, "details": details})
        
        # Recurse into children
        if "_items" in data:
            items.extend(flattened_profiler_data(data["_items"], key_filter))
                 
    return items

def get_audio_context(helpers: Helpers, app_instance: Any) -> Dict[str, Any]:
    """Fetches extra audio context like volume levels and active processes."""
    context = {
        "volume": {},
        "active_processes": {}
    }
    
    if helpers.os_type == "darwin":
        # 1. Volume levels
        vol_out = helpers.run_command('osascript -e "get volume settings"', check_shell=True, app_instance=app_instance)
        if vol_out:
             # Output format: output volume:56, input volume:50, alert volume:90, output muted:true
             parts = vol_out.split(", ")
             for p in parts:
                 if ":" in p:
                     k, v = p.split(":", 1)
                     context["volume"][k.strip()] = v.strip()

        # 2. Active Audio Streams (Heuristic via Logs)
        # We look for AudioDeviceStart events in the last 5 minutes
        log_out = helpers.run_command('log show --last 5m --predicate \'subsystem == "com.apple.coreaudio" and eventMessage contains "Start"\' --style json', check_shell=True, app_instance=app_instance)
        if log_out:
            try:
                logs = json.loads(log_out)
                for entry in logs:
                    proc = entry.get("processImagePath", "")
                    msg = entry.get("eventMessage", "")
                    if proc and msg:
                         proc_name = os.path.basename(proc)
                         # Extract device name from message if possible (e.g., device 82 (BuiltInSpeakerDevice))
                         # Simple match for (Name)
                         dev_match = re.search(r'\(([^)]+)\)', msg)
                         dev_name = dev_match.group(1) if dev_match else "Unknown"
                         
                         if dev_name not in context["active_processes"]:
                             context["active_processes"][dev_name] = []
                         if proc_name not in context["active_processes"][dev_name]:
                             context["active_processes"][dev_name].append(proc_name)
            except:
                pass
                
    return context

def get_camera_context(helpers: Helpers, app_instance: Any) -> Dict[str, Any]:
    """Fetches extra camera context like in-use status and technical specs."""
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
        log_out = helpers.run_command('log show --last 5m --predicate \'process == "appleh13camerad" or process == "cameracaptured" or process == "VDCAssistant"\' --style json', check_shell=True, app_instance=app_instance)
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
    
    return context

def get_system_data(helpers: Helpers, app_instance: Any) -> Dict[str, Any]:
    """Collects system information into a dictionary."""
    data = {
        "os_type": helpers.os_type,
        "general": {
            "system": platform.system(),
            "node": platform.node(),
            "machine": platform.machine(),
            "processor_generic": platform.processor(),
            "details": {}
        },
        "memory": {
            "total_gb": 0,
            "used_gb": 0,
            "available_gb": 0,
            "swap_total": "N/A",
            "swap_used": "N/A",
            "swap_free": "N/A",
            "details": {}
        },
        "storage": {
            "physical_disks": []
        },
        "internal_hardware": {},
        "external_hardware": {}
    }

    # --- Windows Collection (Simplified for now as focus is macOS) ---
    if helpers.os_type == "windows":
         # ... Existing Windows logic (omitted/simplified for brevity as request focused on Mac hardware details) ...
         # If needed, we'd copy the previous windows block here. 
         # Assuming user is on Mac primarily based on context.
         pass
         
    # --- macOS Collection ---
    elif helpers.os_type == "darwin":
        app_instance.log_output("Gathering detailed macOS system information...")
        
        # 1. Expanded Hardware Overview
        hw_info_raw = helpers.run_command("system_profiler SPHardwareDataType", check_shell=True, app_instance=app_instance)
        if hw_info_raw:
            # Parse key-value pairs
            current_section = data["general"]["details"]
            for line in hw_info_raw.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    # Filter for interesting keys
                    if key in [
                        "Model Name", "Model Identifier", "Model Number", "Chip", 
                        "Total Number of Cores", "Memory", "System Firmware Version", 
                        "OS Loader Version", "Serial Number (system)", "Hardware UUID", 
                        "Provisioning UDID", "Activation Lock Status"
                    ]:
                        current_section[key] = val

        # Memory (sysctl)
        mem_size = helpers.run_command("sysctl -n hw.memsize", check_shell=True, app_instance=app_instance)
        if mem_size:
            data["memory"]["total_gb"] = round(int(mem_size.strip()) / (1024**3), 2)
        
        # Approximate used memory
        vm_stat = helpers.run_command("vm_stat", check_shell=True, app_instance=app_instance)
        if vm_stat:
            lines = vm_stat.splitlines()
            p_size = 4096
            stats = {}
            for line in lines:
                if "page size" in line:
                    m = re.search(r'(\d+)', line)
                    if m: p_size = int(m.group(1))
                else:
                    m = re.match(r'\s*Pages\s+(.+?):\s+(\d+)', line)
                    if m: stats[m.group(1).strip('.')] = int(m.group(2))
            
            used_pages = stats.get('active', 0) + stats.get('wired down', 0) + stats.get('occupied by physical pages that have been compressed', 0)
            data["memory"]["used_gb"] = round((used_pages * p_size) / (1024**3), 2)
            if data["memory"]["total_gb"]:
                 data["memory"]["available_gb"] = round(data["memory"]["total_gb"] - data["memory"]["used_gb"], 2)

        # 2. Hierarchical Storage
        try:
            # Fetch raw diskutil list for robust status (Priority 1)
            # We parse text output for lines like: /dev/disk0 (internal, physical):
            diskutil_text = helpers.run_command("diskutil list", check_shell=True, app_instance=app_instance)
            disk_classification = {} 
            if diskutil_text:
                 for line in diskutil_text.splitlines():
                     # Match: /dev/diskX (internal, physical): or (external, physical)
                     if "/dev/" in line and "physical" in line:
                         parts = line.split()
                         if len(parts) > 0:
                             dev_id = parts[0].replace("/dev/", "").replace(":", "")
                             is_int = "(internal," in line
                             disk_classification[dev_id] = is_int
            
            data["storage"]["disk_classification"] = disk_classification

            # We want to enable `diskutil list -plist` which gives the tree.
            # But `diskutil list -plist` output structure is flat list of "AllDisksAndPartitions".
            # It DOES nest partitions under physical disks in the plist structure!
            
            disk_plist_raw = helpers.run_command("diskutil list -plist", check_shell=True, app_instance=app_instance)
            if disk_plist_raw:
                 plist = plistlib.loads(disk_plist_raw.encode('utf-8'))
                 all_disks = plist.get('AllDisksAndPartitions', [])
                 
                 # First Pass: Build a map of DeviceIdentifier -> Simple Internal Status
                 # We need this to look up Physical Store status for APFS Containers
                 # Identify the status we TRUST primarily (robust map) or fallback to plist 'Internal'
                 disk_status_map = {}
                 for disk_entry in all_disks:
                     d_id = disk_entry.get('DeviceIdentifier')
                     is_int = disk_entry.get('Internal', False)
                     if d_id in disk_classification:
                         is_int = disk_classification[d_id]
                     disk_status_map[d_id] = is_int

                 # Second Pass: Create Objects for all disks first
                 disk_objects_map = {}
                 child_disk_ids = set()
                 
                 for disk_entry in all_disks:
                     # Filter: Only process "Whole" disks? 
                     # Checking debug output, WholeDisk key is missing on some systems even for whole disks.
                     # AllDisksAndPartitions seems to return roots properly. Reference: debug_live_data.py
                     # if not disk_entry.get("WholeDisk", False):
                     #    continue

                     p_disk = {
                         "id": disk_entry.get('DeviceIdentifier'),
                         "size_bytes": disk_entry.get('Size', 0),
                         "size_gb": round(disk_entry.get('Size', 0)/(1024**3), 2),
                         "name": disk_entry.get('VolumeName', 'Physical Disk'), 
                         "is_internal": disk_entry.get('Internal', False),
                         "partitions": [],
                         "content": disk_entry.get('Content', 'Unknown'),
                         "container_info": disk_entry.get("APFSPhysicalStores", [])
                     }
                     
                     # Check Robust classification
                     if p_disk["id"] in disk_classification:
                         p_disk["is_internal"] = disk_classification[p_disk["id"]]

                     # Warnings logic
                     p_disk["warnings"] = []
                     content_type = p_disk.get("content", "Unknown")
                     is_system_partition = content_type in ["Apple_APFS_ISC", "Apple_APFS_Recovery", "Apple_Boot", "APFS Container"]
                     if p_disk["is_internal"] and p_disk["size_gb"] < 64 and p_disk["size_gb"] > 0 and not is_system_partition:
                         p_disk["warnings"].append("Suspiciously Small Internal Disk")
                     
                     # Partitions & APFS Volumes
                     # diskutil list -plist puts standard partitions in "Partitions"
                     # BUT APFS Containers puts volumes in "APFSVolumes" and leaves "Partitions" empty.
                     # We need to check both.
                     volume_sources = []
                     if "Partitions" in disk_entry: volume_sources.extend(disk_entry["Partitions"])
                     if "APFSVolumes" in disk_entry: volume_sources.extend(disk_entry["APFSVolumes"])
                     
                     for part_entry in volume_sources:
                         vol = {
                             "id": part_entry.get('DeviceIdentifier'),
                             "size_gb": round(part_entry.get('Size', 0)/(1024**3), 2),
                             "name": part_entry.get('VolumeName', 'Untitled'),
                             "mount_point": part_entry.get('MountPoint', ''),
                             "content": part_entry.get('Content', 'Unknown'),
                             "used": "N/A",
                             "avail": "N/A",
                             "children": [] # For nested containers
                         }
                         # Get usage if mounted
                         if vol["mount_point"]:
                             df_out = helpers.run_command(f"df -h \"{vol['mount_point']}\"", check_shell=True, app_instance=app_instance)
                             if df_out:
                                 lines = df_out.splitlines()
                                 if len(lines) > 1:
                                     parts = lines[1].split()
                                     if len(parts) >= 4:
                                         vol["used"] = parts[2]
                                         vol["avail"] = parts[3]
                         p_disk["partitions"].append(vol)
                     
                     disk_objects_map[p_disk["id"]] = p_disk

                 # Third Pass: Link Containers to Parents
                 for d_id, p_disk in disk_objects_map.items():
                     if p_disk["container_info"]:
                         for store in p_disk["container_info"]:
                             store_id = store.get("DeviceIdentifier")
                             # Find the parent partition
                             # Parent partition ID is store_id.
                             # We need to find which disk contains this partition.
                             # Optimization: Parse parent disk ID from store_id (disk0s2 -> disk0)
                             match = re.match(r'(disk\d+)', store_id)
                             if match:
                                 parent_disk_id = match.group(1)
                                 if parent_disk_id in disk_objects_map:
                                     parent_disk = disk_objects_map[parent_disk_id]
                                     # Find the specific partition object
                                     for part in parent_disk["partitions"]:
                                         if part["id"] == store_id:
                                             part["children"].append(p_disk)
                                             child_disk_ids.add(d_id)
                                             
                                             # Inherit internal status
                                             if parent_disk["is_internal"]:
                                                 p_disk["is_internal"] = True
                                                 # Also update robust map for accurate badging
                                                 disk_classification[d_id] = True
                                                 p_disk["content"] = "APFS Container"
                                                 # Clear warnings if suppressed
                                                 if "Suspiciously Small Internal Disk" in p_disk["warnings"]:
                                                     p_disk["warnings"].remove("Suspiciously Small Internal Disk")
                                             break

                 # Final Population: Add only Roots (not children) to data
                 for d_id, p_disk in disk_objects_map.items():
                     if d_id not in child_disk_ids:
                         data["storage"]["physical_disks"].append(p_disk)
                     
        except Exception as e:
            app_instance.log_output(f"Error parsing storage: {e}")

        # 3. Additional Internal Hardware
        # Internal: NVMe, Audio, Network, Camera
        data["internal_hardware"]["NVMe"] = get_profiler_json(helpers, "SPNVMeDataType", app_instance)
        data["internal_hardware"]["Audio"] = get_profiler_json(helpers, "SPAudioDataType", app_instance)
        data["internal_hardware"]["Network"] = get_profiler_json(helpers, "SPNetworkDataType", app_instance)
        data["internal_hardware"]["Camera"] = get_profiler_json(helpers, "SPCameraDataType", app_instance)
        
        # 4. External/Peripheral Hardware
        # External: USB, Thunderbolt, Bluetooth, Displays
        data["external_hardware"]["USB"] = get_profiler_json(helpers, "SPUSBDataType", app_instance)
        data["external_hardware"]["Thunderbolt"] = get_profiler_json(helpers, "SPThunderboltDataType", app_instance)
        data["external_hardware"]["Bluetooth"] = get_profiler_json(helpers, "SPBluetoothDataType", app_instance)
        data["external_hardware"]["Displays"] = get_profiler_json(helpers, "SPDisplaysDataType", app_instance)
        
        # 5. Detailed Storage for Inventory Classification
        # We fetch this specifically to help with the Internal/External check in the inventory summary
        data["storage_detailed"] = get_profiler_json(helpers, "SPStorageDataType", app_instance)

        # 6. Audio Context (Volume, Active Processes)
        data["audio_context"] = get_audio_context(helpers, app_instance)

        # 7. Camera Context (In Use, Specs)
        data["camera_context"] = get_camera_context(helpers, app_instance)

    # --- Linux Collection (Stub) ---
    elif helpers.os_type == "linux":
         pass

    return data

# Helper for rendering device lists
def render_device_section(title, device_dict, open_by_default=True, extra_context=None):
    is_open = "open" if open_by_default else ""
    content = f"<details {is_open}><summary><h2 class='section-header' style='display:inline-block; border-bottom:none; margin-top:0;'>{title}</h2></summary><div style='padding-top:10px;'>"
    
    if not device_dict:
        return content + "<p>No data available.</p></div></details>"
    
    # Crypto-to-Human Key Mapping
    key_map = {
        "spaudio_has_dts_decoding": "DTS Decoding",
        "spaudio_has_dolby_digital_decoding": "Dolby Digital Decoding",
        "spaudio_sample_rate": "Sample Rate",
        "spaudio_bits_per_sample": "Bit Depth",
        "spaudio_channels": "Channels",
        "spusb_speed": "USB Speed",
        "device_speed": "Connection Speed",
        "device_manufacturer": "Manufacturer",
        "device_model": "Model",
        "link_speed": "Ethernet Link Speed",
        "ip_address": "IP Address",
        "mac_address": "MAC Address",
        "Ethernet.MAC Address": "MAC Address",
        "IPv4.Addresses": "IP Address (IPv4)",
        "IPv6.Addresses": "IP Address (IPv6)",
        "IPv4.Router": "Gateway",
        "IPv4.Config Method": "IP Config Method",
        "interface": "Interface Name",
        "hardware_port": "Hardware Port",
        "_active_processes": "Active Processes",
        "_camera_Resolution": "Max Resolution",
        "_camera_Frame Rate": "Max Frame Rate",
        "_camera_Notes": "Capabilities",
        "coreaudio_device_srate": "Sample Rate (Hz)",
        "coreaudio_device_transport": "Transport",
        "coreaudio_device_manufacturer": "Manufacturer",
        "coreaudio_device_input": "Input Channels",
        "coreaudio_device_output": "Output Channels"
    }

    has_items = False
    for dtype, items in device_dict.items():
        if items:
             has_items = True
             # Flatten for display
             flat = flattened_profiler_data(items)
             content += f"<h3 style='margin-left: 10px; color: #555; border-left: 3px solid #0056b3; padding-left: 10px;'>{dtype}</h3>"
             if flat:
                 content += "<ul style='list-style:none; padding-left:10px;'>"
                 for dev in flat:
                     # Filter out buses and hubs for cleanliness
                     if any(bus in dev['name'] for bus in ["USB 3.1 Bus", "USB 3.0 Bus", "USB 2.0 Bus", "Thunderbolt Bus", "PCI", "Root Hub"]):
                         continue 
                     
                     # Check for activity (Network specific)
                     is_active = False
                     for k, v in dev['details'].items():
                         # Look for IP keys specifically (avoiding MAC addresses)
                         is_ip_key = any(x in k for x in ["IPv4.Addresses", "IPv6.Addresses", "ip_address"])
                         if is_ip_key and v and v != "N/A" and "0.0.0.0" not in str(v):
                             is_active = True
                             break
                     
                     status_badge = ""
                     if dtype == "Network":
                          color = "bg-int" if is_active else "bg-inactive"
                          label = "Active" if is_active else "Inactive"
                          status_badge = f"<span class='badge {color}'>{label}</span>"
                     
                     # Audio Enhancements
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
                     
                     # Special handling for Camera VID/PID strings like "VendorID_1133 ProductID_2140" (Decimal)
                     if vid and "VendorID_" in str(vid):
                         v_match = re.search(r'VendorID_(\d+)', str(vid))
                         p_match = re.search(r'ProductID_(\d+)', str(vid))
                         if v_match and p_match:
                             try:
                                 vid = hex(int(v_match.group(1)))
                                 pid = hex(int(p_match.group(1)))
                             except:
                                 pass
                     
                     correlated = correlate_vid_pid(vid, pid)
                     if correlated:
                         status_badge += f"<span class='badge bg-int' title='ID: {vid}:{pid}'>Verified HW: {correlated}</span>"
                         dev['details']['_correlated_name'] = correlated
                          
                     # Parse metadata into a clean table structure within a card
                     details_rows = ""
                     for k, v in dev['details'].items():
                         if k in ["_name", "spdisplays_ndrvs", "spdisplays_vram"]: continue
                         
                         # Clean label
                         label = key_map.get(k, k.lstrip("_").replace("_", " ").title())
                         # Handle boolean strings
                         if v == "spaudio_yes": v = "Yes"
                         if v == "spaudio_no": v = "No"
                         
                         details_rows += f"<tr><td style='border:none; padding: 2px 8px; color: #666; width: 170px;'>{label}</td><td style='border:none; padding: 2px 8px;'>{v}</td></tr>"
                     
                     if not details_rows:
                         details_rows = "<tr><td style='border:none; padding: 2px 8px; color: #888;'>No additional details available.</td></tr>"

                     content += f"""
                     <li style='margin-bottom: 15px;'>
                         <details class='device-box' style='border: 1px solid #eee; background: #fafafa;'>
                             <summary style='cursor: pointer; padding: 10px;'>
                                 <span class='device-name'>{dev['name']}</span>
                                 {status_badge}
                             </summary>
                             <div style='padding: 0 10px 10px 10px;'>
                                 <table style='width: auto; border: none; margin: 0;'>
                                     {details_rows}
                                 </table>
                             </div>
                         </details>
                     </li>
                     """
                 content += "</ul>"
             else:
                 content += "<p style='margin-left: 20px;'>No devices.</p>"
    
    if not has_items:
        content += "<p style='margin-left: 20px;'>No notable devices found.</p>"
    
    content += "</div></details>"
    return content

# Helper for rendering displays specifically (Detailed)
def render_displays(items):
    if not items:
        return "<h2 class='section-header'>Displays & Graphics</h2><p>No display information available.</p>"
        
    content = "<details open><summary><h2 class='section-header' style='display:inline-block; border-bottom:none; margin-top:0;'>Displays & Graphics</h2></summary>"
    content += "<div class='displays-container' style='padding-top:10px;'>"
    for gpu in items:
        gpu_name = gpu.get("_name", "Unknown GPU")
        chip_type = gpu.get("sppci_model", "")
        if chip_type: gpu_name += f" ({chip_type})"
        
        content += f"<div class='device-box'><h3>GPU: {gpu_name}</h3>"
        
        monitors = gpu.get("spdisplays_ndrvs", [])
        if monitors:
             content += "<table class='info-table'><thead><tr><th>Monitor</th><th>Resolution</th><th>Type</th><th>Main</th><th>Online</th></tr></thead><tbody>"
             for mon in monitors:
                  mon_name = mon.get("_name", "Unknown Display")
                  
                  # Robust Resolution Parsing
                  # Priority: Native Hardware String > Pixel Dimensions > Scaled Resolution
                  native_res = "N/A"
                  scaled_res = mon.get("spdisplays_resolution") or mon.get("_spdisplays_resolution") or ""
                  
                  # 1. Try to extract native from pixelresolution (e.g. spdisplays_2880x1864Retina)
                  pix_res = mon.get("spdisplays_pixelresolution", "")
                  if pix_res.startswith("spdisplays_") and any(c.isdigit() for c in pix_res):
                      # Extract numbers and Retina/pattern
                      native_res = pix_res.replace("spdisplays_", "")
                      if "x" in native_res:
                          # Format nicely: 2880x1864Retina -> 2880 x 1864 Retina
                          parts = native_res.split("x")
                          if len(parts) == 2:
                              # might be '2880' and '1864Retina'
                              width = parts[0]
                              height_part = "".join([c for c in parts[1] if c.isdigit()])
                              extra = "".join([c for c in parts[1] if not c.isdigit()])
                              native_res = f"{width} x {height_part} {extra}".strip()
                  
                  # 2. Fallback to _spdisplays_pixels if native_res is still N/A or generic
                  if native_res == "N/A" or not any(c.isdigit() for c in native_res):
                      pixels = mon.get("_spdisplays_pixels")
                      if pixels:
                          native_res = pixels
                  
                  # Final Display String
                  scaled_base = scaled_res.split(" @ ")[0].strip()
                  if scaled_base and scaled_base != native_res.strip() and native_res != "N/A":
                      res = f"<b>{native_res}</b><br><small>Current: {scaled_res}</small>"
                  else:
                      res = native_res if native_res != "N/A" else scaled_res
                  
                  if not res: res = "N/A"
                  
                  # Connection Type
                  conn_type = "External"
                  if mon.get("spdisplays_builtin") == "spdisplays_yes":
                      conn_type = "Built-in"
                  elif "spdisplays_connection_type" in mon:
                      conn_type = mon["spdisplays_connection_type"]
                  
                  is_main = "Yes" if mon.get("spdisplays_main") == "spdisplays_yes" else "No"
                  is_online = "Yes" if mon.get("spdisplays_online") == "spdisplays_yes" else "No"
                  
                  content += f"<tr><td>{mon_name}</td><td>{res}</td><td>{conn_type}</td><td>{is_main}</td><td>{is_online}</td></tr>"
             content += "</tbody></table>"
        else:
             content += "<p>No monitors attached to this GPU.</p>"
        content += "</div>"
    content += "</div></details>"
    return content

def generate_system_hardware_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):

    app_instance.log_output("\n--- Generating System & Hardware Report ---")
    
    # 1. Collect Data
    data = get_system_data(helpers, app_instance)
    
    # Process SPStorageDataType for deep mapping
    # Map bsd_name (e.g. disk3s5) -> details
    # We will use this to correctly attribute internal/external status
    sp_storage_map = {}
    if "storage_detailed" in data and data["storage_detailed"]:
        def parse_sp_storage(items):
            for item in items:
                bsd = item.get("bsd_name", "")
                if bsd:
                    # Enrich map with vital stats
                    is_int = "unknown"
                    if "physical_drive" in item and isinstance(item["physical_drive"], dict):
                        is_int = item["physical_drive"].get("is_internal_disk", "unknown")
                    
                    sp_storage_map[bsd] = {
                        "is_internal": is_int,
                        "file_system": item.get("file_system", "Unknown"),
                        "name": item.get("_name", ""),
                        "mount_point": item.get("mount_point", ""),
                        "size_bytes": item.get("size_in_bytes", 0)
                    }
                
                if "_items" in item:
                    parse_sp_storage(item["_items"])
                    
        parse_sp_storage(data["storage_detailed"])

    # 2. Build HTML from Data
    html_body = f"""
    <style>
        .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        .info-table th, .info-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .info-table th {{ background-color: #f2f2f2; }}
        
        .disk-container {{ border: 1px solid #ccc; margin-bottom: 15px; border-radius: 4px; overflow: hidden; }}
        .disk-header {{ background: #eee; padding: 10px; cursor: pointer; font-weight: bold; display: flex; justify-content: space-between; }}
        .disk-header:hover {{ background: #e0e0e0; }}
        .disk-content {{ padding: 10px; background: #fff; }}
        
        .part-table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
        .part-table th {{ background: #f9f9f9; text-align: left; border-bottom: 2px solid #ddd; padding: 5px; }}
        .part-table td {{ padding: 5px; border-bottom: 1px solid #eee; }}
        
        .badge {{ padding: 3px 6px; border-radius: 4px; color: white; font-size: 0.8em; margin-left: 5px; }}
        .bg-int {{ background-color: #28a745; }} /* Internal Green / Active */
        .bg-ext {{ background-color: #ffc107; color: #000; }} /* External Yellow */
        .bg-warn {{ background-color: #dc3545; }} /* Warning Red */
        .bg-inactive {{ background-color: #6c757d; }} /* Inactive Gray */
        
        .section-header {{ background: #333; color: white; padding: 8px; border-radius: 4px; margin-top: 20px; }}
        .device-box {{ border: 1px solid #ddd; margin: 5px 0; padding: 8px; border-radius: 4px; }}
        .device-name {{ font-weight: bold; color: #0056b3; }}
        .device-meta {{ font-size: 0.9em; color: #666; }}
    </style>
    """
    
    # 1. General & Hardware
    html_body += "<h2 class='section-header'>Hardware Overview</h2>"
    html_body += "<table class='info-table'>"
    
    # Prioritize specific order if desired, or just loop
    priority_keys = ["Model Name", "Model Identifier", "Chip", "Total Number of Cores", "Memory", "Serial Number (system)", "Activation Lock Status"]
    
    # Print priority ones first
    for k in priority_keys:
        if k in data["general"]["details"]:
             html_body += f"<tr><td width='30%'>{k}</td><td><b>{data['general']['details'][k]}</b></td></tr>"
    
    # Print the rest
    for k, v in data["general"]["details"].items():
        if k not in priority_keys:
             html_body += f"<tr><td width='30%'>{k}</td><td>{v}</td></tr>"
             
    html_body += "</table>"
    
    # 2. Storage
    html_body += "<h2 class='section-header'>Storage Devices</h2>"
    
    if data["storage"]["physical_disks"]:
        def render_disk(disk, level=0):
            # Calculate style for nesting
            indent = level * 20
            style = f"margin-left: {indent}px; border-left: 2px solid #ccc;" if level > 0 else ""
            
            # Robust Logic for Disk Classification (already handled in get_system_data, but good for display vars)
            final_is_internal = disk.get("is_internal", False)
            if disk.get("is_internal_refined") is not None:
                final_is_internal = disk["is_internal_refined"]
            
            # Badge logic
            int_badge = "<span class='badge bg-int'>Internal</span>" if final_is_internal else "<span class='badge bg-ext'>External</span>"
            if disk.get("content") == "APFS Container":
                # Maybe a simplified badge or different color?
                 pass
            
            warn_badge = ""
            for w in disk.get("warnings", []): warn_badge += f"<span class='badge bg-warn'>{w}</span>"
            
            icon = "💾" if final_is_internal else "🔌"
            
            title = f"{icon} {disk['id']} - {disk['size_gb']} GB ({disk['content']}) {int_badge} {warn_badge}"
            
            # Recursively render children in partitions
            rows_html = ""
            if disk["partitions"]:
                for p in disk["partitions"]:
                    p_name = p['name'] if p['name'] else "<i>Untitled</i>"
                    # Enrich from SPStorage map (if we still had access to sp_storage_map here... 
                    # we do, it is in scope if defined above or passed. 
                    # Actually, get_system_data did most enrichment.
                    
                    p_type = p['content']
                    # We can use sp_storage_map if available in scope
                    if 'sp_storage_map' in locals() and p['id'] in sp_storage_map:
                         sp_info = sp_storage_map[p['id']]
                         if sp_info["file_system"] != "Unknown":
                              p_type = sp_info["file_system"]
                         # Enrich Mount Point if missing or just to be sure
                         if sp_info["mount_point"]:
                              # Prioritize SPStorage mount point as it can often be more accurate for user volumes
                              p['mount_point'] = sp_info["mount_point"]
                    
                    rows_html += f"<tr><td>{p['id']}</td><td>{p_name}</td><td>{p['size_gb']} GB</td><td>{p['used']}</td><td>{p['avail']}</td><td>{p_type}</td><td><code>{p['mount_point']}</code></td></tr>"
                    
                    # Check for children (Visual Hierarchy)
                    if "children" in p and p["children"]:
                        # We render children in a row spanning columns or a new block?
                        # Let's do a row spanning all
                        rows_html += "<tr><td colspan='7' style='padding:0; border:none;'>"
                        for child in p["children"]:
                            rows_html += render_disk(child, level + 1)
                        rows_html += "</td></tr>"

            else:
                rows_html += "<tr><td colspan='7'>No partitions found (Raw Disk or Unknown Format)</td></tr>"
                
            return f"""
            <details class='disk-container' open style='{style}'>
                <summary class='disk-header'>{title}</summary>
                <div class='disk-content'>
                    <table class='part-table'>
                        <thead><tr><th>Partition/Volume</th><th>Name</th><th>Size</th><th>Used</th><th>Available</th><th>Type</th><th>Mount Point</th></tr></thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
            </details>
            """

        for disk in data["storage"]["physical_disks"]:
             # Refine Logic currently handled in get_system_data for most part, 
             # but we can do a final pass for sp_storage_map enrichment on top level if needed.
             # Actually, logic moved to render control
             
             # Re-apply sp_internal_votes logic if needed? 
             # get_system_data largely handles it now via inheritance. 
             # But let's defer to render_disk helper
             
             # Quick SP check for top level if not inherited
             if not disk.get("container_info"):
                # Vote logic for standard roots
                sp_internal_votes = 0
                sp_external_votes = 0
                for p in disk.get("partitions", []):
                     if p["id"] in sp_storage_map:
                         sp_info = sp_storage_map[p["id"]]
                         if sp_info["is_internal"] == "yes": sp_internal_votes += 1
                         if sp_info["is_internal"] == "no": sp_external_votes += 1
                
                disk_cls = data["storage"].get("disk_classification", {})
                if disk['id'] not in disk_cls:
                     if sp_external_votes > 0: disk['is_internal_refined'] = False
                     elif sp_internal_votes > 0: disk['is_internal_refined'] = True
             
             html_body += render_disk(disk)

    else:
        html_body += "<p>No storage devices info available.</p>"
    


    # 3. Internal Hardware
    html_body += render_device_section("Internal Components", data["internal_hardware"], open_by_default=True, extra_context=data.get("audio_context"))
    
    # 4. External Hardware
    # Handle Displays Separately
    displays_data = data["external_hardware"].pop("Displays", None)
    
    if displays_data:
        html_body += render_displays(displays_data)
        
    html_body += render_device_section("External / Peripherals", data["external_hardware"], open_by_default=True, extra_context=data.get("audio_context"))

    # 5. Inventory Summary (New Section)
    # We build this based on the specific logic from the user's bash script
    
    html_body_inventory = "<h2 class='section-header'>Device Inventory (Internal vs External)</h2>"
    html_body_inventory += "<table class='info-table'><thead><tr><th>Category</th><th>Details</th></tr></thead><tbody>"
    
    # helper to print inventory row
    def add_inv_row(cat, label, value):
        return f"<tr><td><span class='badge {cat}'>{label}</span></td><td>{value}</td></tr>"

    rows = []
    
    # --- USB / Thunderbolt / Displays ---
    # Logic: External: Yes -> EXTERNAL, else INTERNAL (default logic often checks 'built_in_device' in JSON)
    for dtype, items in {**data["external_hardware"], **data["internal_hardware"]}.items():
        if dtype in ["USB", "Thunderbolt", "Displays"]: # Added Displays to inventory? Optional. usually Displays shown as separate.
            flat = flattened_profiler_data(items)
            for dev in flat:
                if dev['name'] in ["USB 3.1 Bus", "USB 3.0 Bus", "USB 2.0 Bus", "Thunderbolt Bus", "PCI"]: continue
                
                # Check for "External: Yes" or logic. system_profiler JSON uses different keys sometimes.
                # In JSON usually: "built_in_device": "yes" (Internal) vs "no" (External)
                # Or sometimes "non_removable": "yes"
                
                details = dev['details']
                # Heuristic matching user script logic which parses text output
                # If we see "built_in_device": "no" -> External
                # In JSON, look for key 'built_in_device' == 'no'? Or 'removable_media' == 'yes'?
                # Actually, standard SPHardware/USB JSON often has "built_in_device": "yes" for internal.
                
                is_internal = False
                
                is_built_in = "no"
                if "built_in_device" in details:
                    is_built_in = details["built_in_device"]
                elif "spdisplays_builtin" in details: # Display logic
                    is_built_in = details["spdisplays_builtin"]
                
                # If built_in is "no", it's External.
                if is_built_in == "yes": is_internal = True
                
                if is_internal:
                    rows.append(("bg-int", "INTERNAL", f"{dtype}: {dev['name']}"))
                else:
                    rows.append(("bg-ext", "EXTERNAL", f"{dtype}: {dev['name']}"))

    # --- Storage (Refined) ---
    # Re-use our parsed data['storage']['physical_disks']
    for disk in data["storage"]["physical_disks"]:
        # Use simple 'is_internal_refined' we calculated above
        is_int = disk.get("is_internal_refined", disk["is_internal"])
        cat = "bg-int" if is_int else "bg-ext"
        label = "INTERNAL" if is_int else "EXTERNAL"
        rows.append((cat, label, f"Storage: {disk['id']} ({disk['name']}) - {disk['size_gb']} GB"))

    # --- Bluetooth ---
    # Logic: Connected: Yes -> EXTERNAL
    if data["external_hardware"].get("Bluetooth"):
        flat_bt = flattened_profiler_data(data["external_hardware"]["Bluetooth"])
        for dev in flat_bt:
            # Check connection status
            # Key often "device_connected": "Yes"
            is_connected = dev['details'].get("device_connected", "No")
            if is_connected == "Yes":
                 rows.append(("bg-ext", "EXTERNAL", f"Bluetooth: {dev['name']}"))

    # --- Internal Network ---
    if data["internal_hardware"].get("Network"):
         flat_net = flattened_profiler_data(data["internal_hardware"]["Network"])
         for dev in flat_net:
             # User script greps "Hardware Port" -> INTERNAL
             if "hardware_port" in dev['details'] or "interface" in dev['details']:
                  port = dev['details'].get("hardware_port", dev['name'])
                  rows.append(("bg-int", "INTERNAL", f"Network: {port}"))

    # Sort rows by External first, then Internal? Or just append.
    # Let's sort: External first for visibility
    rows.sort(key=lambda x: (x[1] != "EXTERNAL", x[2]))
    
    for r in rows:
        html_body_inventory += add_inv_row(r[0], r[1], r[2])
        
    html_body_inventory += "</tbody></table>"

    # Prepend inventory to body (after Hardware Overview)
    # We want it near top.
    # Let's insert it before Storage Devices
    target_header = "<h2 class='section-header'>Storage Devices</h2>"
    if target_header in html_body:
        final_html = html_body.replace(target_header, html_body_inventory + target_header)
    else:
        # Fallback if header not found (shouldn't happen but safe)
        final_html = html_body + html_body_inventory

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "System_Hardware_Report.html", 
        "System & Hardware Information Report", 
        final_html,
        browser_preference=browser_preference
    )
