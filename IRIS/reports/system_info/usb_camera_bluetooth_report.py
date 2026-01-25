import sys
import plistlib
import re
from typing import List, Dict, Any, Optional
from ...helpers import MockAppInstance, Helpers
from ...analysis.security_advisor import SecurityAdvisor

def _recursive_find_items(items: List[Dict], results: List[Dict], category: str):
    """
    Recursively traverse system_profiler tree and collect items.
    """
    for item in items:
        if isinstance(item, dict):
            # Heuristic: if it has a name and some ID, it's likely a device
            name = item.get('_name', item.get('name'))
            if name:
                 # Flatten basic details
                 flat = {
                     "name": name,
                     "category": category,
                     "manufacturer": item.get('manufacturer', item.get('maker', 'N/A')),
                     "vendor_id": item.get('vendor_id', item.get('ua_vendor_id', 'N/A')),
                     "product_id": item.get('product_id', item.get('ua_product_id', 'N/A')),
                     "serial": item.get('serial_num', item.get('variable_speed', 'N/A')), # serial_num sometimes mismatch
                     "details": {k:v for k,v in item.items() if k not in ['_name', '_items']}
                 }
                 results.append(flat)
            
            if '_items' in item and isinstance(item['_items'], list):
                _recursive_find_items(item['_items'], results, category)

def get_device_data(helpers: Helpers, app_instance: Any) -> Dict[str, Any]:
    """Collects connected device information."""
    data = {
        "os_type": helpers.os_type,
        "usb": [],
        "usb_tree": [],
        "camera": [],
        "audio": [],
        "bluetooth": []
    }

    if helpers.os_type == "darwin":
        app_instance.log_output("Gathering macOS Device info...")
        
        # USB - Hierarchical Parsing via ioreg
        import subprocess
        try:
             raw_ioreg = helpers.run_command(["ioreg", "-p", "IOUSB", "-w0", "-l"], app_instance=app_instance)
        except Exception as e:
             app_instance.log_output(f"Error running ioreg directly: {e}")
             raw_ioreg = ""
             
        if raw_ioreg:
             lines = raw_ioreg.splitlines()
             root = {"name": "Host (Laptop)", "raw_name": "Root", "children": [], "depth": -1}
             stack = [root] 
             current_node = None
             
             for line in lines:
                 node_match = re.search(r'^([ \t|]*)\+\-o (.+?)  <class', line)
                 if node_match:
                     indent_str = node_match.group(1)
                     raw_name = node_match.group(2).strip()
                     depth = len(indent_str)
                     
                     new_node = {
                         "raw_name": raw_name,
                         "name": raw_name, 
                         "children": [],
                         "depth": depth,
                         "properties": {},
                         "text_block": "" 
                     }
                     
                     while stack and stack[-1]["depth"] >= depth:
                         stack.pop()
                     parent = stack[-1]
                     parent["children"].append(new_node)
                     stack.append(new_node)
                     current_node = new_node
                 elif current_node:
                     current_node["text_block"] += line + "\n"
                     
             data["usb_tree"] = root["children"]
             
             def process_node(node):
                 text = node["text_block"]
                 def get_prop(key, text):
                     pat = r'"' + re.escape(key) + r'"\s*=\s*(.*)'
                     m = re.search(pat, text)
                     if m:
                         val = m.group(1).strip()
                         if val.startswith('"') and val.endswith('"'): return val[1:-1]
                         return val
                     return None
                 
                 current_draw = get_prop("kUSBDeviceCurrent", text) or get_prop("kUSBDeviceRequiredVoltage", text)
                 speed = get_prop("kUSBDeviceSpeed", text)
                 location_id = get_prop("locationID", text)
                 vid = get_prop("idVendor", text)
                 pid = get_prop("idProduct", text)
                 vendor_name = get_prop("USB Vendor Name", text)
                 product_name = get_prop("USB Product Name", text)
                 serial = get_prop("USB Serial Number", text)
                 
                 vid = str(vid) if vid else "0"
                 pid = str(pid) if pid else "0"
                 try:
                     vid_hex = f"0x{int(vid):04x}" if vid.isdigit() else vid
                     pid_hex = f"0x{int(pid):04x}" if pid.isdigit() else pid
                 except:
                     vid_hex, pid_hex = vid, pid
                     
                 # --- Enhanced Naming Context ---
                 display_name = product_name if product_name else node["raw_name"]
                 
                 # Contextual renames
                 if "Root" in node["raw_name"]:
                     display_name = "Host (Laptop)"
                 elif "AppleT" in node["raw_name"] or "AppleUSB" in node["raw_name"]:
                     # Likely a controller/root hub
                     if node.get("depth", 0) < 5: # Top level
                         display_name = "Thunderbolt/USB-C Port"
                 
                 if "Hub" in display_name and vendor_name:
                     display_name = f"{vendor_name} Hub"

                 node["chart_label"] = display_name
                 node["vid_hex"] = vid_hex
                 node["pid_hex"] = pid_hex
                 node["serial"] = serial if serial else "N/A"
                 node["unique_id"] = f"{vid_hex}:{pid_hex}:{serial}"
                 
                 details_dict = {
                     "Source": "ioreg", 
                     "Raw Name": node["raw_name"],
                     "Location ID": location_id
                 }
                 if current_draw: details_dict["Power (mA)"] = current_draw
                 if speed: 
                     speed_map = {"0": "Low", "1": "Full", "2": "High", "3": "Super", "4": "Super+"}
                     details_dict["Speed"] = speed_map.get(speed, speed)
                 
                 node["details"] = details_dict
                 
                 item = {
                     "name": display_name,
                     "category": "USB",
                     "manufacturer": vendor_name if vendor_name else "N/A",
                     "vendor_id": vid_hex,
                     "product_id": pid_hex,
                     "serial": serial if serial else "N/A",
                     "details": details_dict
                 }
                 data['usb'].append(item)
                 
                 kept_children = []
                 for child in node["children"]:
                     process_node(child)
                     is_root_child = (node.get("raw_name") == "Root" or "Root" in node.get("name", ""))
                     is_duplicate = (child["vid_hex"] == node["vid_hex"] and child["pid_hex"] == node["pid_hex"])
                     
                     child_vid = child["vid_hex"]
                     has_bad_vid = (child_vid == "0" or child_vid == "0x0000")
                     is_generic_name =("IOUSB" in child.get("name","") or "Root" in child.get("name",""))
                     is_likely_garbage = (has_bad_vid and is_generic_name)
                     
                     if is_root_child: kept_children.append(child)
                     elif not is_duplicate and not is_likely_garbage: kept_children.append(child)
                 node["children"] = kept_children

             for root_node in data["usb_tree"]:
                 process_node(root_node)

        if not data['usb']:
            try:
                xml = helpers.run_command("system_profiler -xml SPUSBDataType", check_shell=True, app_instance=app_instance)
                if xml:
                    plist = plistlib.loads(xml.encode('utf-8'))
                    if plist and len(plist) > 0 and '_items' in plist[0]:
                        _recursive_find_items(plist[0]['_items'], data['usb'], "USB")
            except Exception: pass

        try:
            xml = helpers.run_command("system_profiler -xml SPCameraDataType SPAudioDataType", check_shell=True, app_instance=app_instance)
            if xml:
                plist = plistlib.loads(xml.encode('utf-8'))
                for dtype_data in plist:
                    dtype_name = dtype_data.get('_dataType', '')
                    items = dtype_data.get('_items', [])
                    if dtype_name == 'SPCameraDataType':
                        _recursive_find_items(items, data['camera'], "Camera")
                    elif dtype_name == 'SPAudioDataType':
                        _recursive_find_items(items, data['audio'], "Audio")
        except Exception: pass
             
        try:
            xml = helpers.run_command("system_profiler -xml SPBluetoothDataType", check_shell=True, app_instance=app_instance)
            if xml:
                plist = plistlib.loads(xml.encode('utf-8'))
                if plist and len(plist) > 0 and '_items' in plist[0]:
                    _recursive_find_items(plist[0]['_items'], data['bluetooth'], "Bluetooth")
        except Exception: pass

    elif helpers.os_type == "linux":
        app_instance.log_output("Gathering Linux Device info (lsusb)...")
        lsusb = helpers.run_command("lsusb", app_instance=app_instance)
        if lsusb:
            for line in lsusb.splitlines():
                m = re.match(r'Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+([0-9a-fA-F:]+)\s+(.+)', line)
                if m:
                    vid_pid = m.group(3)
                    name = m.group(4)
                    vid, pid = vid_pid.split(':') if ':' in vid_pid else (vid_pid, 'N/A')
                    data['usb'].append({
                        "name": name,
                        "category": "USB",
                        "manufacturer": "N/A",
                        "vendor_id": vid,
                        "product_id": pid,
                        "serial": "N/A",
                        "details": {"Bus": m.group(1), "Device": m.group(2)}
                    })
    
    _post_process_device_data(data, app_instance)
    
    try:
        xml = helpers.run_command("system_profiler -xml SPDisplaysDataType", check_shell=True, app_instance=app_instance)
        if xml:
             plist = plistlib.loads(xml.encode('utf-8'))
             if plist and len(plist) > 0 and '_items' in plist[0]:
                 data['displays'] = []
                 for d in plist[0]['_items']:
                     data['displays'].append({
                         "name": d.get('_name', 'Unknown Display'),
                         "resolution": d.get('_resolution', 'N/A'),
                         "connection_type": d.get('spdisplays_connection_type', 'N/A')
                     })
    except: pass
    
    return data

def _parse_usb_ids(file_path: str = "usb.ids") -> Dict[str, Any]:
    db = {}
    current_vendor_id = None
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.rstrip()
                if not line or line.startswith('#'): continue
                if line.startswith('\t') and current_vendor_id:
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) >= 2:
                        try: db[current_vendor_id]["products"][f"0x{int(parts[0], 16):04x}"] = parts[1]
                        except: pass
                elif not line.startswith('\t') and not line.startswith('C'): 
                    parts = line.split(maxsplit=1)
                    if len(parts) >= 2 and len(parts[0]) == 4:
                        try:
                            vid_hex = f"0x{int(parts[0], 16):04x}"
                            db[vid_hex] = {"name": parts[1], "products": {}}
                            current_vendor_id = vid_hex
                        except: current_vendor_id = None
                        else: current_vendor_id = None
    except FileNotFoundError: return {} 
    return db

def _post_process_device_data(data: Dict[str, Any], app_instance: Any):
    usb_db = _parse_usb_ids("usb.ids")
    
    # Deduplicate USB
    unique_devices = {}
    cleaned_list = []
    for dev in data['usb']:
        vid = dev.get('vendor_id', '0')
        pid = dev.get('product_id', '0')
        serial = dev.get('serial', 'N/A')
        name = dev.get('name', '')
        
        # Skip garbage
        if ((vid=='0' or vid=='0x0000') and (pid=='0' or pid=='0x0000') and ("IOUSB" in name or "Root" in name)): continue
             
        key = f"{vid}:{pid}:{serial}"
        if key == "0:0:N/A": key = name
        if key not in unique_devices:
            unique_devices[key] = dev
            cleaned_list.append(dev)
    data['usb'] = cleaned_list

    # Enrich with usb.ids
    for dev in data['usb']:
        vid = dev.get('vendor_id', '').lower()
        pid = dev.get('product_id', '').lower()
        if vid in usb_db:
            if dev.get('manufacturer') in ['N/A', 'Unknown', vid]: dev['manufacturer'] = usb_db[vid]['name']
            if pid in usb_db[vid]['products']:
                mapped_name = usb_db[vid]['products'][pid]
                if "USB" in dev['name'] or "Hub" in dev['name'] or len(dev['name']) < 5:
                     dev['name'] = mapped_name
                     
    # Enrich Cameras
    usb_lookup = {}
    for d in data['usb']:
        if d.get('vendor_id') and d.get('product_id'): 
            usb_lookup[(d['vendor_id'], d['product_id'])] = d
            
    for cam in data['camera']:
        model_id = cam.get('details', {}).get('spcamera_model-id', '')
        m = re.search(r'VendorID_(\d+)\s+ProductID_(\d+)', model_id)
        best_match = None
        if m:
            v, p = f"0x{int(m.group(1)):04x}", f"0x{int(m.group(2)):04x}"
            best_match = usb_lookup.get((v, p))
        
        if not best_match:
            # Name match
            for u in data['usb']:
                if u['name'] == cam['name']: 
                    best_match = u
                    break
                    
        if best_match:
            cam['vendor_id'] = best_match['vendor_id']
            cam['product_id'] = best_match['product_id']
            if 'details' not in cam: cam['details'] = {}
            cam['details'].update(best_match['details'])

def _unify_devices(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Merges USB, Camera, and Audio into unified composite devices."""
    unified_map = {} # serial -> obj
    
    # 1. Start with USB devices as the physical base
    for dev in data['usb']:
        # Create a unique key. Serial is best. VID:PID fallback.
        serial = dev.get('serial', 'N/A')
        vid = dev.get('vendor_id', '')
        pid = dev.get('product_id', '')
        name = dev.get('name', 'Unknown')
        
        key = serial if serial != 'N/A' else f"{vid}:{pid}:{name}"
        
        unified_map[key] = {
            "name": name,
            "manufacturer": dev.get("manufacturer", "N/A"),
            "serial": serial,
            "hw_ids": [f"{vid}:{pid}"],
            "capabilities": ["USB"],
            "details": dev.get("details", {})
        }

    # 2. Merge Cameras
    for cam in data['camera']:
        serial = cam.get('serial', 'N/A')
        name = cam.get('name', '')
        vid = cam.get('vendor_id', '')
        pid = cam.get('product_id', '')
        
        key = serial if serial != 'N/A' else f"{vid}:{pid}:{name}"
        
        # Fuzzy match if key not found (try name)
        if key not in unified_map:
             # Try finding by name
             found = False
             for k, u in unified_map.items():
                 if u['name'] == name:
                     key = k
                     found = True
                     break
             if not found:
                 # Create new standalone camera
                 unified_map[key] = {
                    "name": name,
                    "manufacturer": cam.get("manufacturer", "N/A"),
                    "serial": serial,
                    "hw_ids": [],
                    "capabilities": ["Camera"],
                    "details": cam.get("details", {})
                 }
                 
        # Enrich existing
        obj = unified_map[key]
        if "Camera" not in obj["capabilities"]: obj["capabilities"].append("Camera")
        obj["details"].update(cam.get("details", {}))

    # 3. Merge Audio
    for aud in data['audio']:
        name = aud.get('name', '')
        # Audio usually has no useful IDs in system_profiler
        # Match by name
        matched = False
        for k, u in unified_map.items():
            # If audio name is substring of device name or vice versa
            if name in u['name'] or u['name'] in name:
                if "Audio" not in u["capabilities"]: u["capabilities"].append("Audio")
                u["details"]["Audio Sample Rate"] = aud.get('details', {}).get('coreaudio_device_srate', 'N/A')
                matched = True
                break
        
        if not matched:
             unified_map[name] = {
                 "name": name,
                 "manufacturer": aud.get("manufacturer", "N/A"),
                 "serial": "N/A",
                 "capabilities": ["Audio"],
                 "details": {"Sample Rate": aud.get('details', {}).get('coreaudio_device_srate', 'N/A')}
             }

    return list(unified_map.values())

def generate_usb_camera_bluetooth_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    app_instance.log_output("\n--- Generating Expert Unified Peripherals Report ---")
    data = get_device_data(helpers, app_instance)
    unified_devices = _unify_devices(data)
    
    
    # --- Project Shine: Build Volume Map & Storage List ---
    # Moved to top to power both the Graph and the Table
    volume_map = {}
    storage_list = []
    
    if sys.platform == "darwin":
        try:
            raw_list = helpers.run_command("diskutil list -plist", check_shell=True, app_instance=app_instance)
            if raw_list:
                import plistlib
                plist = plistlib.loads(raw_list.encode('utf-8'))
                all_disks = plist.get('AllDisksAndPartitions', [])
                
                # 1. Map Physical Stores -> Synthesized Containers (APFS)
                store_map = {}
                for d in all_disks:
                    if 'APFSPhysicalStores' in d:
                        for ps in d['APFSPhysicalStores']:
                            ps_id = ps.get('DeviceIdentifier')
                            if ps_id: store_map[ps_id] = d

                # 2. Iterate ALL disks and check Status via Info
                for d in all_disks:
                     did = d.get('DeviceIdentifier')
                     # Optimization: Only check root-like disks (skip partitions s1, s2 if possible, but safe to check all)
                     # We use 'Partitions' presence as hint it's a parent, or check if it has content.
                     
                     # Get Full Info to determine Internal/External (since plist 'Internal' key was missing)
                     info_raw = helpers.run_command(f"diskutil info -plist {did}", check_shell=True, app_instance=app_instance)
                     if info_raw:
                         info = plistlib.loads(info_raw.encode('utf-8'))
                         
                         # Check External
                         is_external = info.get('Ejectable') is True or info.get('Internal') is False
                         # Also exclude disk images if desired, but user wants flash drives.
                         
                         if is_external:
                             # It is an external drive.
                             loc_id = info.get('LocationID')
                             
                             # Fallback: Parse DeviceTreePath for LocationID (Critical for some external drives)
                             if not loc_id and info.get('DeviceTreePath'):
                                 try:
                                     dt = info.get('DeviceTreePath')
                                     if '@' in dt:
                                         # Standard format: .../usb-drd1-port-hs@01100000
                                         suffix = dt.split('@')[-1].split('/')[0]
                                         loc_id = int(suffix, 16)
                                 except: pass

                             size = info.get('TotalSize', 0)
                             size_str = f"{round(size / (1024**3), 2)} GB"
                             
                             # Resolve Volumes (using d structure + store_map)
                             volumes = []
                             
                             # Check direct volumes (ExFAT etc)
                             if 'VolumeName' in info and info['VolumeName']:
                                 volumes.append(info['VolumeName'])
                             
                             # Check Partitions from the List Dict (d)
                             if 'Partitions' in d:
                                 for p in d['Partitions']:
                                     vn = p.get('VolumeName')
                                     if vn: volumes.append(vn)
                                     
                                     # Check APFS Link
                                     pid = p.get('DeviceIdentifier')
                                     if pid in store_map:
                                         container = store_map[pid]
                                         for cp in container.get('Partitions', []):
                                             cvn = cp.get('VolumeName')
                                             if cvn: volumes.append(f"{cvn}") # (APFS) inferred
                             
                             # Deduplicate volumes
                             volumes = list(set(volumes))
                             vol_str = ", ".join(volumes)
                             
                             # Populate Map
                             if loc_id and volumes:
                                 try:
                                     volume_map[int(loc_id)] = vol_str
                                     # Handle hex string too
                                     volume_map[int(loc_id, 0)] = vol_str 
                                 except: pass
                             
                             # Add to Storage List (only if not already added? diskutil list flat? no tree)
                             # We only want to list the Root Physical Disks in the table.
                             # If 'Partitions' key exists, it's likely a root or container.
                             if 'Partitions' in d or is_external: 
                                 # We filter out slices like disk6s1 if disk6 is present
                                 # Logic: If we found volumes, it's worth listing.
                                 if size > 0:
                                     storage_list.append({
                                         "id": did,
                                         "size": size_str,
                                         "volumes": vol_str or "(No Mounted Volumes)"
                                     })

        except Exception as e:
            app_instance.log_output(f"Storage Scan Error: {e}")

    html_body = "<h2>Connected Peripheral Devices (Unified View)</h2>"

    
    # --- Expert Mermaid Chart (Project Shine) ---
    if 'usb_tree' in data and data['usb_tree']:
        html_body += "<h3>Physical Device Topology</h3>"
        
        # Legend (Project Shine)
        html_body += """
        <div style='background:#f9f9f9; padding:10px; border:1px solid #ddd; border-radius:4px; margin: 10px 0; font-size: 0.9em;'>
        <b>Map Legend:</b> &nbsp;
        💻 Host &nbsp;|&nbsp; 
        🔀 Hub &nbsp;|&nbsp; 
        💾 Storage (Check for [Vol: Name]) &nbsp;|&nbsp; 
        ⌨️/🖱️ Input &nbsp;|&nbsp; 
        📷/🎧 A/V &nbsp;|&nbsp; 
        🖥️ Display &nbsp;|&nbsp; 
        [1.2] Physical Path
        </div>
        """
        
        # Icons switched to Emojis (Native)

        
        html_body += "<p><i>Visualizing physical connections with Dewey Decimal Path (e.g., [1.2]) and inferred Port Numbers.</i></p>"
        html_body += '<div class="mermaid">\n'
        html_body += "graph LR;\n"
        
        counter = 0
        node_registry = {} # "dedup_key" -> "nodeX"

        def get_dedup_key(node):
            vid = node.get("vid_hex", "0")
            pid = node.get("pid_hex", "0")
            serial = node.get("serial", "N/A")
            name = node.get("name", "")
            
            # 1. Strongest: VID+PID+Serial
            if serial != "N/A" and serial and len(serial) > 3:
                 return f"{vid}:{pid}:{serial}"
            
            # 2. Medium: Hubs with specific names
            if "Hub" in name or "Adapter" in name:
                 return f"{vid}:{pid}:{name}"
                 
            # 3. Weak: Object Identity
            return f"obj_{id(node)}"

        def get_icon(name, is_root=False):
            if is_root: return "💻"
            l = name.lower()
            if "hub" in l: return "🔀"
            if "keyboard" in l: return "⌨️"
            if "mouse" in l or "trackpad" in l: return "🖱️"
            if "camera" in l or "video" in l: return "📷"
            if "audio" in l or "speaker" in l or "mic" in l or "headset" in l: return "🎧"
            if "iphone" in l or "phone" in l or "mobile" in l: return "📱"
            if "bluet" in l: return "📶"
            if "storage" in l or "flash" in l or "drive" in l or "disk" in l: return "💾"
            if "lan" in l or "ethernet" in l or "network" in l: return "🌐"
            if "display" in l or "monitor" in l or "billboard" in l: return "🖥️"
            return "🔌"

        def clean(txt): return txt.replace('"', '').replace('(', '').replace(')', '').replace('[', '').replace(']', '').replace("'", "")

        def add_tree(node, parent_id=None, path_str=""):
            nonlocal html_body, counter
            
            key = get_dedup_key(node)
            is_new_node = False
            
            if key in node_registry:
                my_id = node_registry[key]
            else:
                my_id = f"node{counter}"
                counter += 1
                node_registry[key] = my_id
                is_new_node = True
            
            name = node.get("chart_label", node.get("name", "Device"))
            
            # Styles & Label
            dewey_label = f"[{path_str}]" if path_str else "[Host]"
            clean_name = clean(name)
            
            # Root Node is always Host
            is_root = (parent_id is None)
            if is_root: 
                clean_name = "Host (Laptop)"
                dewey_label = ""
            
            # Special Rename for Billboard -> HDMI/Video
            if "billboard" in name.lower():
                clean_name = "HDMI/Video Adapter"
            
            # Volume Mapping (Project Shine)
            details = node.get("details", {})
            loc_id_str = details.get("Location ID")
            if loc_id_str:
                try:
                    lid = int(loc_id_str, 0)
                    if lid in volume_map:
                         clean_name = f"{clean_name}<br/>[Vol: {volume_map[lid]}]"
                         icon = "💾" # Force Floppy 
                except: pass

            icon = get_icon(name, is_root)
            lbl = f"{icon} {clean_name}<br/>{dewey_label}"
            
            if is_new_node:
                # Styles
                if is_root:
                     html_body += f'    {my_id}("{lbl}")\n    style {my_id} fill:#f96,stroke:#333,stroke-width:2px,color:black\n'
                elif "Hub" in name:
                     html_body += f'    {my_id}{{"{lbl}"}}\n    style {my_id} fill:#aff,stroke:#333,color:black\n'
                elif "Port" in name and "Thunderbolt" in name:
                     html_body += f'    {my_id}(("{lbl}"))\n    style {my_id} fill:#9f9,stroke:#333,color:black\n'
                else:
                     html_body += f'    {my_id}["{lbl}"]\n'

            # Define Edge (Always draw edge for visual topology, even if node exists)
            if parent_id:
                # Port Number from Path
                port_str = path_str.split('.')[-1]
                edge_label = f"|Port {port_str}|"
                html_body += f"    {parent_id} -->{edge_label} {my_id}\n"
            
            # Recurse
            children = node.get("children", [])
            for i, child in enumerate(children, 1): 
                next_path = f"{path_str}.{i}" if path_str else f"{i}"
                add_tree(child, my_id, next_path)

        for i, root in enumerate(data['usb_tree'], 1):
             if not root.get("children"): continue
             add_tree(root, path_str=f"{i}") # Host is virtual root, so these are actually ROOT PORTS

        html_body += "</div>\n"
        html_body += "<script src='https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js'></script>\n"
        html_body += "<script>mermaid.initialize({startOnLoad:true, securityLevel:'loose'});</script>\n"
        html_body += "<hr/>"

    # --- Unified Table ---
    html_body += "<h3>Connected Devices (Unified List)</h3>"
    html_body += "<table><thead><tr><th>Name</th><th>Type/Capabilities</th><th>Manufacturer</th><th>Serial / Connection ID</th><th>Details</th></tr></thead><tbody>"
    
    # Sort: Hubs first, then composite, then single
    def sort_key(d):
        score = 0
        if "Hub" in d['name']: score = -10
        if len(d['capabilities']) > 1: score -= 5
        return score
        
    for dev in sorted(unified_devices, key=sort_key):
        caps = ", ".join(dev['capabilities'])
        det_str = "<br/>".join([f"<b>{k}:</b> {str(v)}" for k,v in dev['details'].items() if not k.startswith('_') and k != "Source"])
        
        html_body += f"<tr><td>{dev['name']}</td><td>{caps}</td><td>{dev['manufacturer']}</td><td>{dev['serial']}</td><td>{det_str}</td></tr>"

    html_body += "</tbody></table>"
    
    # Displays Table (New)
    if 'displays' in data:
         html_body += "<h3>Connected Displays</h3>"
         html_body += "<table><thead><tr><th>Name</th><th>Resolution</th><th>Connection</th></tr></thead><tbody>"
         for d in data['displays']:
             html_body += f"<tr><td>{d['name']}</td><td>{d['resolution']}</td><td>{d['connection_type']}</td></tr>"
         html_body += "</tbody></table>"

    # --- NEW: USB Storage Table (Attached USB Storage) ---
    # Render the data collected at the start
    if sys.platform == "darwin" and storage_list:
        html_body += "<h3>Attached USB Storage</h3>"
        html_body += "<table><thead><tr><th>Physical Disk</th><th>Size</th><th>Volumes</th></tr></thead><tbody>"
        for s in storage_list:
            html_body += f"<tr><td>{s['id']}</td><td>{s['size']}</td><td>{s['volumes']}</td></tr>"
        html_body += "</tbody></table>"
    elif sys.platform == "darwin":
        html_body += "<h3>Attached USB Storage</h3>"
        html_body += "<p>No External Storage identified.</p>"


    # USB Table (Standard)
    html_body += "<h3>USB Devices List</h3>"
    
    helpers.generate_report_html(
        app_instance,
        app_instance.suspect_computer_name,
        "USB_Camera_Bluetooth_Report.html",
        "Expert Unified Peripherals Report",
        html_body,
        browser_preference=browser_preference
    )
