import platform
import sys
import json
import re
import datetime
import glob
import os
import plistlib
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple, Union

# --- Data classes for structured reporting ---
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
    type: str       # e.g., "Physical Disk", "Partition"
    size_gb: float
    used: Optional[str] = None
    available: Optional[str] = None
    filesystem: Optional[str] = None
    mount_point: Optional[str] = None
    serial: Optional[str] = None
    volume_name: Optional[str] = None
    device_identifier: Optional[str] = None
    # Add other fields like SMART health if easily retrievable
# --- END Data classes ---


# --- Mocking helpers and app_instance for standalone testing ---

class MockAppInstance:
    """A mock object to simulate the IRISApp instance for testing."""
    def __init__(self):
        self.suspect_computer_name = "TEST_COMPUTER"
        self.log_messages = [] # To capture log output

    def log_output(self, message):
        """Mocks the log_output method to print to console and store messages."""
        print(f"[MOCK LOG]: {message}")
        self.log_messages.append(message)

# Mock data for system_profiler -xml outputs (REPLACE WITH YOUR ACTUAL OUTPUTS)
MOCK_USB_PLIST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<array>
	<dict>
		<key>_dataType</key>
		<string>SPUSBDataType</string>
		<key>_items</key>
		<array>
			<dict>
				<key>_name</key>
				<string>USB30Bus</string>
				<key>_items</key>
				<array>
					<dict>
						<key>_name</key>
						<string>4-Port USB 3.1 Hub</string>
						<key>manufacturer</key>
						<string>Generic</string>
						<key>product_id</key>
						<string>0x0411</string>
						<key>vendor_id</key>
						<string>0x0bda</string>
						<key>location_id</key>
						<string>0x14900000 / 9</string>
					</dict>
					<dict>
						<key>_name</key>
						<string>Elements SE SSD</string>
						<key>manufacturer</key>
						<string>Western Digital</string>
						<key>product_id</key>
						<string>0x2655</string>
						<key>vendor_id</key>
						<string>0x1058</string>
						<key>serial_num</key>
						<string>323330394458343030303832</string>
						<key>location_id</key>
						<string>0x14944000 / 15</string>
					</dict>
				</array>
			</dict>
			<dict>
				<key>_name</key>
				<string>Bluetooth USB Host Controller</string>
				<key>manufacturer</key>
				<string>Broadcom Corp.</string>
				<key>product_id</key>
				<string>0x8296</string>
				<key>vendor_id</key>
				<string>apple_vendor_id</string>
				<key>location_id</key>
				<string>0x14500000</string>
			</dict>
		</array>
	</dict>
</array>
</plist>
""" # PASTE YOUR ACTUAL SPUSBDataType XML OUTPUT HERE (as bytes, i.e., b"...")

MOCK_CAMERA_PLIST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<array>
	<dict>
		<key>_dataType</key>
		<string>SPCameraDataType</string>
		<key>_items</key>
		<array>
			<dict>
				<key>_name</key>
				<string>FaceTime HD Camera (Built-in)</string>
				<key>manufacturer</key>
				<string>Apple Inc.</string>
				<key>model_id</key>
				<string>UVC Camera VendorID_1452 ProductID_34066</string>
				<key>unique_id</key>
				<string>0x1452851200000000</string>
			</dict>
			<dict>
				<key>_name</key>
				<string>Microsoft® LifeCam VX-2000</string>
				<key>manufacturer</key>
				<string>Microsoft</string>
				<key>model_id</key>
				<string>USB Camera VendorID_045e ProductID_0761</string>
				<key>unique_id</key>
				<string>0x045E076100000000</string>
			</dict>
		</array>
	</dict>
</array>
</plist>
""" # PASTE YOUR ACTUAL SPCameraDataType XML OUTPUT HERE (as bytes, i.e., b"...")

MOCK_BLUETOOTH_PLIST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<array>
	<dict>
		<key>_dataType</key>
		<string>SPBluetoothDataType</string>
		<key>_items</key>
		<array>
			<dict>
				<key>_name</key>
				<string>Apple Bluetooth Software</string>
				<key>manufacturer</key>
				<string>Apple (0x75)</string>
				<key>vendor_id</key>
				<string>0x05ac</string>
				<key>product_id</key>
				<string>0x828d</string>
				<key>Address</key>
				<string>XX-XX-XX-XX-XX-XX</string>
				<key>device_class_of_service</key>
				<string>0x00000000</string>
				<key>class_of_device</key>
				<string>0x00000000</string>
				<key>connected</key>
				<false/>
				<key>_items</key>
				<array>
					<dict>
						<key>_name</key>
						<string>Magic Mouse 2</string>
						<key>manufacturer</key>
						<string>Apple Inc. (0x004c)</string>
						<key>vendor_id</key>
						<string>0x05ac</string>
						<key>product_id</key>
						<string>0x0310</string>
						<key>device_address</key>
						<string>YY-YY-YY-YY-YY-YY</string>
						<key>device_class_of_service</key>
						<string>0x00000100</string>
						<key>class_of_device</key>
						<string>0x002580</string>
						<key>connected</key>
						<true/>
					</dict>
					<dict>
						<key>_name</key>
						<string>My AirPods Pro</string>
						<key>manufacturer</key>
						<string>Apple Inc. (0x004c)</string>
						<key>vendor_id</key>
						<string>0x05ac</string>
						<key>product_id</key>
						<string>0x0311</string>
						<key>device_address</key>
						<string>ZZ-ZZ-ZZ-ZZ-ZZ-ZZ</string>
						<key>connected</key>
						<true/>
					</dict>
                    <dict>
                        <key>Ansible</key>
                        <dict>
                            <key>device_address</key>
                            <string>8C:08:AA:51:63:37</string>
                            <key>device_rssi</key>
                            <string>-47</string>
                        </dict>
                    </dict>
                    <dict>
                        <key>DOOM TV</key>
                        <dict>
                            <key>device_address</key>
                            <string>04:4B:ED:A3:67:A8</string>
                            <key>device_rssi</key>
                            <string>-73</string>
                        </dict>
                    </dict>
				</array>
			</dict>
		</array>
	</dict>
</array>
</plist>
""" # PASTE YOUR ACTUAL SPBluetoothDataType XML OUTPUT HERE (as bytes, i.e., b"...")

MOCK_DISKUTIL_PLIST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>AllDisks</key>
	<array>
		<string>disk0</string>
		<string>disk0s1</string>
		<string>disk1</string>
		<string>disk1s1</string>
	</array>
	<key>AllDisksAndPartitions</key>
	<array>
		<dict>
			<key>Content</key>
			<string>GUID_partition_scheme</string>
			<key>DeviceIdentifier</key>
			<string>disk0</string>
			<key>IOContent</key>
			<string>GUID_partition_scheme</string>
			<key>IORegistryEntryName</key>
			<string>APPLE SSD SM0256F</string>
			<key>Partitions</key>
			<array>
				<dict>
					<key>Content</key>
					<string>EFI</string>
					<key>DeviceIdentifier</key>
					<string>disk0s1</string>
					<key>MountPoint</key>
					<string>/Volumes/EFI</string>
					<key>Size</key>
					<integer>314572800</integer>
					<key>VolumeName</key>
					<string>EFI</string>
				</dict>
				<dict>
					<key>Content</key>
					<string>Apple_APFS</string>
					<key>DeviceIdentifier</key>
					<string>disk0s2</string>
					<key>Size</key>
					<integer>250790432768</integer>
					<key>VolumeName</key>
					<string>Container disk1</string>
				</dict>
			</array>
			<key>Size</key>
			<integer>250790432768</integer>
			<key>VirtualOrPhysical</key>
			<string>Physical Disk</string>
		</dict>
	</array>
</dict>
</plist>
""" # PASTE YOUR ACTUAL diskutil list -plist XML OUTPUT HERE (as bytes, i.e., b"...")


class Helpers:
    """A mock object to simulate the helpers module for testing."""
    def __init__(self, app_instance):
        self.app_instance = app_instance

    def log_output(self, app_instance, message):
        """Mocks log_output to use the mock app_instance's logger."""
        app_instance.log_output(message)

    def run_command(self, command, check_shell=False, app_instance=None):
        """Mocks run_command to return predefined outputs for specific commands."""
        command_str = ' '.join(command) if isinstance(command, list) else command
        
        if "system_profiler -xml SPUSBDataType" in command_str:
            return MOCK_USB_PLIST_XML # Return bytes for plistlib
        elif "system_profiler -xml SPCameraDataType" in command_str:
            return MOCK_CAMERA_PLIST_XML # Return bytes for plistlib
        elif "system_profiler -xml SPBluetoothDataType" in command_str:
            return MOCK_BLUETOOTH_PLIST_XML # Return bytes for plistlib
        elif "system_profiler SPSoftwareDataType" in command_str:
            return """
System Version: macOS 13.7.6 (22H625)
  Kernel Version: Darwin 22.6.0
  Boot Volume: Macintosh HD
  Boot Mode: Normal
  Computer Name: MyMac
  User Name: Test User
  Secure Virtual Memory: Enabled
  System Integrity Protection: Enabled
  Time since boot: 1 day 2 hours
""" # PASTE YOUR ACTUAL SPSoftwareDataType OUTPUT HERE
        elif "system_profiler SPHardwareDataType" in command_str:
            return """
Hardware:

    Hardware Overview:

      Model Name: iMac
      Model Identifier: iMac18,3
      Processor Name: Quad-Core Intel Core i5
      Processor Speed: 3 GHz
      Total Number of Cores: 4
      Number of Processors: 1
      L2 Cache (per Core): 256 KB
      L3 Cache: 6 MB
      Memory: 16 GB
      Boot ROM Version: 1968.120.12.0.0
      SMC Version (system): 2.41f1
      Serial Number (system): C02XXXXXJ1G5
      Hardware UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
""" # PASTE YOUR ACTUAL SPHardwareDataType OUTPUT HERE
        elif "sysctl -n hw.memsize" in command_str:
            return "17179869184" # 16 GB in bytes
        elif "vm_stat" in command_str:
            return """
Mach Virtual Memory Statistics: (page size of 4096 bytes)
Pages free:                            175114.
Pages active:                         1559494.
Pages inactive:                       1629854.
Pages speculative:                      28564.
Pages wired down:                      610212.
Pages throttled:                            0.
Pages purgeable:                            0.
Pages purged:                               0.
File-backed pages:                    1370000.
Anonymous pages:                      1819348.
Pages stored in compressor:                 0.
Pages occupied by physical pages that have been decompressed: 0.
Pages decompressed:                         0.
Pages used for kernel stacks:           16896.
Pages for other data:                  593316.
""" # PASTE YOUR ACTUAL vm_stat OUTPUT HERE
        elif "sysctl vm.swapusage" in command_str:
            return "vm.swapusage: total = 1024.00M  used = 21.50M  free = 1002.50M  (encrypted)" # PASTE YOUR ACTUAL sysctl vm.swapusage OUTPUT HERE
        elif "diskutil list -plist" in command_str:
            return MOCK_DISKUTIL_PLIST_XML # Return bytes for plistlib
        elif "df -h" in command_str:
            # Mock df -h output for a mount point like /System/Volumes/Data
            if "/System/Volumes/Data" in command_str:
                return """
Filesystem     Size   Used  Avail Use% Mounted on
/dev/disk1s1s1  233G   150G    80G  65% /System/Volumes/Data
""" # PASTE YOUR ACTUAL df -h OUTPUT FOR A MOUNT POINT HERE
            return "" # Default empty for other df -h calls
        elif "sudo netstat -an" in command_str:
            return """
Active Internet connections (including servers)
Proto Recv-Q Send-Q  Local Address          Foreign Address        (state)
tcp4       0      0  127.0.0.1.5000         127.0.0.1.59765        ESTABLISHED
tcp4       0      0  192.168.1.100.50000    172.217.160.142.443    ESTABLISHED
tcp4       0      0  *.80                   *.* LISTEN
"""
        elif "sudo ls" in command_str:
            # Mock listing for LaunchDaemons/Agents
            if "/Library/LaunchDaemons" in command_str:
                return "com.apple.coreservices.launchservicesd.plist\ncom.example.mydaemon.plist"
            elif "/Library/LaunchAgents" in command_str:
                return "com.example.myagent.plist"
            elif "/etc/cron.daily" in command_str:
                return "daily_script.sh"
            return ""
        elif "sudo cat" in command_str:
            if "/etc/crontab" in command_str:
                return "# This is a sample crontab file\n0 0 * * * root /usr/local/bin/daily_backup.sh"
            return ""
        elif "crontab -l" in command_str:
            return "# no crontab for spencer\n"
        elif "ps aux" in command_str:
            return """
USER               PID  %CPU %MEM      VSZ    RSS   TT  STAT STARTED      TIME COMMAND
root                 1   0.0  0.0 46067080  20880   ??  Ss   14Jul25  0:09.12 /sbin/launchd
spencer            500   0.1  0.5 48729000 160000   ??  S    14Jul25  0:15.34 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
spencer            501   0.0  0.1 48700000  30000   ??  S    14Jul25  0:00.50 /usr/bin/python3 -c "import base64; exec(base64.b64decode('cHJpbnQoIkhlbGxvIGZyb20gYmFzZTY0ISIp'))"
"""
        elif "wmic" in command_str: # Basic mock for Windows commands
            if "TotalPhysicalMemory" in command_str:
                return "\nTotalPhysicalMemory\n17179869184\n"
            elif "FreePhysicalMemory" in command_str:
                return "\nFreePhysicalMemory  FreeVirtualMemory  TotalVisibleMemorySize  TotalVirtualMemorySize\n8000000             16000000           16000000                32000000\n"
            elif "diskdrive get Caption" in command_str:
                return "\nCaption=APPLE SSD SM0256F\nSerialNumber=S0L123456789\nSize=256060514304\n\nCaption=Samsung Portable SSD T7\nSerialNumber=S6XENS0W606752A\nSize=1000204886016\n"
            elif "logicaldisk get Caption" in command_str:
                return "\nCaption=C:\nFreeSpace=100000000000\nSize=250000000000\nFileSystem=NTFS\n"
            elif "Win32_USBHub" in command_str:
                return "\nDescription=USB Root Hub (USB 3.0)\nDeviceID=USB\\ROOT_HUB30\\4&12345678&0&0\nPNPDeviceID=USB\\ROOT_HUB30\\4&12345678&0&0\n"
            elif "Win32_PnPEntity where \"ConfigManagerErrorCode = 0 and (Name like '%camera%')\"" in command_str:
                return "\nName=Integrated Webcam\nDeviceID=USB\\VID_0BDA&PID_5710\\5&12345678&0&1\n"
            elif "Win32_PnPEntity where \"ConfigManagerErrorCode = 0 and (Name like '%bluetooth%')\"" in command_str:
                return "\nName=Intel(R) Wireless Bluetooth(R)\nDeviceID=USB\\VID_8087&PID_0AAA\\5&12345678&0&1\n"
            elif "Get-Process" in command_str:
                return """
Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id ProcessName
-------  ------    -----      -----     ------     -- -----------
    889      29    50000      70000      12.34   1234 chrome
    120       5     8000      15000       0.50   5678 python
"""
            elif "Get-Service" in command_str:
                return """
Status   Name               DisplayName
------   ----               -----------
Running  BITS               Background Intelligent Transfer Service
Stopped  Dnscache           DNS Client
"""
            return ""
        
        # Default for unrecognized commands
        app_instance.log_output(f"MOCK: Unrecognized command: {command_str}")
        return ""

    def get_report_folder_path(self, suspect_computer_name, report_name):
        """Mocks report folder path to a local 'TEST_REPORTS' folder."""
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        report_folder = os.path.join(desktop_path, f"{suspect_computer_name} IRIS REPORTS")
        os.makedirs(report_folder, exist_ok=True)
        return os.path.join(report_folder, report_name)

    def generate_report_html(self, app_instance, suspect_computer_name, report_filename, title, html_body, open_in_browser=True, browser_preference="System Default"):
        """Mocks generate_report_html to save a local file and print a message."""
        report_path = self.get_report_folder_path(suspect_computer_name, report_filename)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title} - {suspect_computer_name}</title> 
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }} 
        h1 {{ color: #333; }} 
        h2 {{ color: #0066cc; }} 
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; margin-bottom: 20px;}} 
        th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }} 
        th {{ background-color: #f2f2f2; }} 
        .disallowed-rule {{ color: red; }} 
        .active {{ color: #009900; }}
        .inactive {{ color: #FF0000; }} 
        pre {{ background-color: #f9f9f9; padding: 10px; border: 1px solid #ddd; white-space: pre-wrap; word-break: break-all; }}
    </style>
</head>
<body>
    <h1>{title} - {suspect_computer_name}</h1>
    <p>Report generated on: {current_time}</p>
    {html_body}
</body>
</html>
"""
        try:
            with open(report_path, "w", encoding='utf-8') as f:
                f.write(html_content)
            app_instance.log_output(f"MOCK: Report generated and saved to: {report_path}")
            # Do not open in browser automatically for mock
        except Exception as e:
            app_instance.log_output(f"MOCK ERROR: Error generating mock report {report_filename}: {e}")

    def read_plist_file(self, filepath, app_instance=None):
        """Mocks read_plist_file to return predefined plist data."""
        # For diskutil, we return the mock XML directly as bytes, so plistlib.loads can handle it.
        # For other plists (e.g., LaunchDaemons), you'd need to mock based on filepath.
        if "diskutil list -plist" in filepath: # This is a simplified check, adjust if needed
            try:
                return plistlib.loads(MOCK_DISKUTIL_PLIST_XML)
            except Exception as e:
                app_instance.log_output(f"MOCK ERROR: Failed to load mock diskutil plist: {e}")
                return None
        elif "com.example.mydaemon.plist" in filepath:
            # Example for a mock LaunchDaemon plist
            return {
                "Label": "com.example.mydaemon",
                "ProgramArguments": ["/usr/local/bin/mydaemon", "--start"],
                "RunAtLoad": True,
                "KeepAlive": False
            }
        elif "com.example.myagent.plist" in filepath:
            # Example for a mock LaunchAgent plist
            return {
                "Label": "com.example.myagent",
                "Program": "/Applications/MyApp.app/Contents/MacOS/MyApp",
                "RunAtLoad": True
            }
        app_instance.log_output(f"MOCK: Unrecognized plist file for mocking: {filepath}")
        return None

# --- NEW/UPDATED: Helper functions for parsing system_profiler XML output ---

def _extract_nested_devices(item: Dict[str, Any], device_list: List[Dict[str, str]], profile_type: str, app_instance: Any):
    """Recursively flatten devices for USB and Camera, or handle Bluetooth specifically."""
    if profile_type in ['USB', 'Camera']:
        _extract_flat_device(item, device_list, profile_type, app_instance)

        # Recurse if children present (e.g., USB devices under a hub)
        if '_items' in item and isinstance(item['_items'], list):
            for subitem in item['_items']:
                if isinstance(subitem, dict):
                    _extract_nested_devices(subitem, device_list, profile_type, app_instance)
                else:
                    helpers.log_output(app_instance, f"Warning: Skipping non-dictionary subitem in _items for {profile_type}: {type(subitem)} - {str(subitem)[:100]}")

    elif profile_type == 'Bluetooth':
        _extract_bluetooth_devices(item, device_list, app_instance)
    else:
        helpers.log_output(app_instance, f"Warning: Unknown profile_type '{profile_type}' passed to _extract_nested_devices.")


def _extract_flat_device(item: Dict[str, Any], device_list: List[Dict[str, str]], profile_type: str, app_instance: Any):
    """Extract flat data for USB and Camera, appending to device_list."""
    device_info = {}

    # Helper to extract hex ID from strings like "0x046d (Logitech Inc.)"
    def get_hex_id(value):
        if isinstance(value, str):
            match = re.match(r'(0x[0-9a-fA-F]+)', value)
            if match:
                return match.group(1)
            # Handle cases like "apple_vendor_id" which is a string but not a hex
            if value.lower() == "apple_vendor_id":
                return "Apple Inc." # Or keep as "apple_vendor_id" if raw is preferred
        return value if value is not None else "N/A"

    # Common keys and their potential variations in system_profiler output
    # Prioritize '_name' then 'Name'
    name = item.get("_name", item.get("Name", "N/A"))
    # Prioritize 'manufacturer' then '_SPManufacturer'
    manufacturer = item.get("manufacturer", item.get("_SPManufacturer", "N/A"))
    product_id = get_hex_id(item.get("product_id", item.get("Product ID", "N/A")))
    vendor_id = get_hex_id(item.get("vendor_id", item.get("Vendor ID", "N/A")))
    serial_num = item.get("serial_num", item.get("Serial Number", "N/A"))
    location_id = item.get("location_id", item.get("Location ID", "N/A"))
    model_id = item.get("model_id", item.get("Model ID", "N/A"))
    unique_id = item.get("unique_id", item.get("Unique ID", "N/A"))

    if profile_type == 'USB':
        device_info["_name"] = name
        device_info["manufacturer"] = manufacturer
        device_info["product_id"] = product_id
        device_info["vendor_id"] = vendor_id
        device_info["serial_num"] = serial_num
        device_info["location_id"] = location_id

    elif profile_type == 'Camera':
        device_info["_name"] = name
        device_info["manufacturer"] = manufacturer
        device_info["model_id"] = model_id
        device_info["unique_id"] = unique_id
    
    # Only append if we actually extracted some meaningful data
    # Check if any key has a value other than "N/A" or is not empty for strings
    if device_info and any(v != "N/A" and (isinstance(v, str) and v.strip() != "" or not isinstance(v, str)) for v in device_info.values()):
        device_list.append(device_info)
    else:
        helpers.log_output(app_instance, f"Debug: Skipping empty or N/A device_info for {profile_type}: {item.get('_name', 'N/A')}")


def _extract_bluetooth_devices(item: Dict[str, Any], device_list: List[Dict[str, str]], app_instance: Any):
    """Handle host controller and connected Bluetooth devices, appending to device_list."""
    
    # Helper to extract hex ID from strings like "0x046d (Logitech Inc.)"
    def get_hex_id(value):
        if isinstance(value, str):
            match = re.match(r'(0x[0-9a-fA-F]+)', value)
            if match:
                return match.group(1)
        return value if value is not None else "N/A"

    # Helper to convert boolean 'connected' to 'Yes'/'No'
    def get_connected_status(value):
        if isinstance(value, bool):
            return "Yes" if value else "No"
        return str(value) if value is not None else "N/A"

    # Extract host controller details (top-level item)
    # Ensure all expected keys are present, even if N/A
    host_controller = {
        "_name": item.get("_name", item.get("Name", "N/A")),
        "manufacturer": item.get("manufacturer", item.get("_SPManufacturer", "N/A")),
        "vendor_id": get_hex_id(item.get("vendor_id", item.get("Vendor ID", "N/A"))),
        "product_id": get_hex_id(item.get("product_id", item.get("Product ID", "N/A"))),
        "address": item.get("Address", "N/A"), # Note: 'Address' (capital A) for host controller
        "device_address": item.get("device_address", "N/A"), # Sometimes host controller has this too
        "device_class_of_service": item.get("device_class_of_service", "N/A"),
        "class_of_device": item.get("class_of_device", "N/A"),
        "is_connected": get_connected_status(item.get("connected")) # Host controller can be "connected" to system
    }
    # Only add if it has some meaningful data beyond just "N/A"
    if any(v != "N/A" and (isinstance(v, str) and v.strip() != "" or not isinstance(v, str)) for v in host_controller.values()):
        device_list.append(host_controller)
    else:
        helpers.log_output(app_instance, f"Debug: Skipping empty or N/A Bluetooth host controller: {item.get('_name', 'N/A')}")


    # Iterate through all values that are dictionaries or lists of dictionaries
    # This handles connected devices that might be direct children or within lists
    for key, value in item.items():
        # Heuristic: If a value is a dict and contains typical device keys, it's a device
        if isinstance(value, dict) and any(k in value for k in ["device_address", "Address", "_name", "Name", "manufacturer"]):
            bt_device = {
                "_name": value.get("_name", value.get("Name", key)), # Use _name, then Name, then dict key
                "manufacturer": value.get("manufacturer", "N/A"),
                "vendor_id": get_hex_id(value.get("vendor_id", "N/A")),
                "product_id": get_hex_id(value.get("product_id", "N/A")),
                "address": value.get("Address", "N/A"),
                "device_address": value.get("device_address", "N/A"),
                "device_class_of_service": value.get("device_class_of_service", "N/A"),
                "class_of_device": value.get("class_of_device", "N/A"),
                "is_connected": get_connected_status(value.get("connected"))
            }
            if any(v != "N/A" and (isinstance(v, str) and v.strip() != "" or not isinstance(v, str)) for v in bt_device.values()):
                device_list.append(bt_device)
            else:
                helpers.log_output(app_instance, f"Debug: Skipping empty or N/A Bluetooth device_info for key {key}: {str(value)[:100]}")

        elif isinstance(value, list):
            # This handles lists of connected devices, like 'connected_devices' list
            for sub_item in value:
                if isinstance(sub_item, dict) and any(k in sub_item for k in ["device_address", "Address", "_name", "Name", "manufacturer"]):
                    bt_device = {
                        "_name": sub_item.get("_name", sub_item.get("Name", "N/A")),
                        "manufacturer": sub_item.get("manufacturer", "N/A"),
                        "vendor_id": get_hex_id(sub_item.get("vendor_id", "N/A")),
                        "product_id": get_hex_id(sub_item.get("product_id", "N/A")),
                        "address": sub_item.get("Address", "N/A"),
                        "device_address": sub_item.get("device_address", "N/A"),
                        "device_class_of_service": sub_item.get("device_class_of_service", "N/A"),
                        "class_of_device": sub_item.get("class_of_device", "N/A"),
                        "is_connected": get_connected_status(sub_item.get("connected"))
                    }
                    if any(v != "N/A" and (isinstance(v, str) and v.strip() != "" or not isinstance(v, str)) for v in bt_device.values()):
                        device_list.append(bt_device)
                    else:
                        helpers.log_output(app_instance, f"Debug: Skipping empty or N/A Bluetooth sub_item device_info: {str(sub_item)[:100]}")
                else:
                    helpers.log_output(app_instance, f"Warning: Skipping non-device dictionary in Bluetooth list: {str(sub_item)[:100]}")
        else:
            # Log other top-level keys that are not dicts or lists, if they are not common ones
            # These are usually metadata or irrelevant entries
            if key not in ["_dataType", "_items", "SPDisplaysDataType", "SPUSBDataType", "SPCameraDataType", "SPBluetoothDataType", "SPNVMeDataType", "SPSerialATADataType"]: # Avoid logging known data types
                helpers.log_output(app_instance, f"Debug: Skipping non-dict/non-list top-level item in Bluetooth data: {key}: {type(value)} - {str(value)[:100]}")


def _process_sp_device_data(plist_bytes: bytes, data_type_key: str, app_instance: Any) -> List[Dict[str, str]]:
    """Entry point to process the top-level plist structure for system_profiler output."""
    parsed_devices = []
    if not plist_bytes:
        return parsed_devices
    
    try:
        plist_root = plistlib.loads(plist_bytes)

        actual_items_to_process = []

        if isinstance(plist_root, list) and len(plist_root) > 0 and isinstance(plist_root[0], dict):
            root_dict = plist_root[0]
            if root_dict.get('_dataType') == data_type_key:
                items_list = root_dict.get('_items', [])
                if isinstance(items_list, list):
                    actual_items_to_process.extend(items_list)
                else:
                    helpers.log_output(app_instance, f"Warning: Expected '_items' in {data_type_key} to be a list, got {type(items_list)} instead. Raw: {str(items_list)[:200]}...")
            else:
                # Fallback if _dataType doesn't match or is missing, but relevant keys are at root_dict
                # This check is less precise but might catch some edge cases
                if any(key in root_dict for key in ['_name', 'Name', 'manufacturer', '_SPManufacturer', 'product_id', 'Product ID', 'vendor_id', 'Vendor ID', 'Address', 'device_address', 'connected_devices', 'model_id', 'Model ID', 'unique_id', 'Unique ID']):
                    actual_items_to_process = [root_dict]
                else:
                    helpers.log_output(app_instance, f"Warning: {data_type_key} _dataType mismatch or missing. Raw root_dict: {str(root_dict)[:200]}...")
        elif isinstance(plist_root, dict):
            # Fallback for older macOS versions or specific data types that might just return a single dict at root
            if any(key in plist_root for key in ['_name', 'Name', 'manufacturer', '_SPManufacturer', 'product_id', 'Product ID', 'vendor_id', 'Vendor ID', 'Address', 'device_address', 'connected_devices', 'model_id', 'Model ID', 'unique_id', 'Unique ID']):
                actual_items_to_process = [plist_root]
            else:
                helpers.log_output(app_instance, f"Warning: {data_type_key} top-level is dict but no relevant keys found. Raw: {str(plist_root)[:200]}...")
        else:
            helpers.log_output(app_instance, f"Error: Expected plist root to be a list or dict for {data_type_key}, got {type(plist_root)}. Raw: {str(plist_root)[:200]}...")
            return parsed_devices
        
        for item in actual_items_to_process:
            # Pass the simplified profile_type (e.g., 'USB', 'Camera', 'Bluetooth')
            _extract_nested_devices(item, parsed_devices, data_type_key.replace('SP', '').replace('DataType', ''), app_instance) 

    except plistlib.InvalidFileException:
        helpers.log_output(app_instance, f"Error: system_profiler {data_type_key} -xml output not valid. Snippet: {plist_bytes.decode('utf-8', errors='ignore')[:500]}...")
    except Exception as e:
        helpers.log_output(app_instance, f"Unexpected error parsing {data_type_key} info: {e}")
    
    return parsed_devices


def sys_info(app_instance, helpers, browser_preference="System Default"):
    """Gathers and reports general system information."""
    helpers.log_output(app_instance, "\nRunning System Info Report....")
    
    html_body = "" # Start with empty string, build sections below

    # --- General System Information ---
    html_body += "<h2>General System Information</h2><table><tr><th>Attribute</th><th>Value</th></tr>"
    html_body += f"<tr><td>System</td><td>{platform.system()}</td></tr>"
    html_body += f"<tr><td>Node Name</td><td>{platform.node()}</td></tr>"
    html_body += f"<tr><td>Machine Architecture</td><td>{platform.machine()}</td></tr>"
    html_body += f"<tr><td>Processor (Generic)</td><td>{platform.processor()}</td></tr>"
    
    if sys.platform == "win32":
        helpers.log_output(app_instance, "Gathering detailed Windows system information...")
        output_os = helpers.run_command('systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Manufacturer" /C:"System Model" /C:"Processor(s)" /C:"Total Physical Memory"', app_instance=app_instance)
        if output_os:
            for line in output_os.strip().split('\n'):
                if ":" in line:
                    attr, val = line.split(":", 1)
                    html_body += f"<tr><td>{attr.strip()}</td><td>{val.strip()}</td></tr>"
    
    elif sys.platform == "darwin":
        helpers.log_output(app_instance, "Gathering detailed macOS system information using `system_profiler`...")

        # --- macOS Specific OS and CPU Info ---
        try:
            # SPSoftwareDataType for OS Version
            sw_info = helpers.run_command("system_profiler SPSoftwareDataType", check_shell=True, app_instance=app_instance)
            if sw_info:
                os_match = re.search(r'System Version: (.+)', sw_info)
                build_match = re.search(r'Build Version: (.+)', sw_info)
                if os_match: html_body += f"<tr><td>macOS Version</td><td>{os_match.group(1).strip()}</td></tr>"
                if build_match: html_body += f"<tr><td>macOS Build</td><td>{build_match.group(1).strip()}</td></tr>"
            
            # SPHardwareDataType for detailed CPU
            hw_info = helpers.run_command("system_profiler SPHardwareDataType", check_shell=True, app_instance=app_instance)
            if hw_info:
                processor_match = re.search(r'Processor Name: (.+)', hw_info)
                speed_match = re.search(r'Processor Speed: (.+)', hw_info)
                cores_match = re.search(r'Total Number of Cores: (.+)', hw_info)
                if processor_match: html_body += f"<tr><td>Processor (Detailed)</td><td>{processor_match.group(1).strip()}</td></tr>"
                if speed_match: html_body += f"<tr><td>Processor Speed</td><td>{speed_match.group(1).strip()}</td></tr>"
                if cores_match: html_body += f"<tr><td>Number of Cores</td><td>{cores_match.group(1).strip()}</td></tr>"
        except Exception as e:
            helpers.log_output(app_instance, f"Error gathering macOS OS/CPU details: {e}")
            html_body += f"<tr><td colspan='2'>Error gathering detailed macOS OS/CPU info.</td></tr>"

    html_body += """</table>""" # End General System Info table

    # --- Memory Information ---
    html_body += "<h2>Memory (RAM) Information</h2><table><tr><th>Metric</th><th>Value</th></tr>"
    if sys.platform == "darwin":
        try:
            # sysctl for total physical memory
            total_mem_kb_str = helpers.run_command("sysctl -n hw.memsize", check_shell=True, app_instance=app_instance)
            if total_mem_kb_str:
                total_mem_gb = round(int(total_mem_kb_str.strip()) / (1024**3), 2)
                html_body += f"<tr><td>Total Physical Memory</td><td>{total_mem_gb} GB</td></tr>"
            else:
                helpers.log_output(app_instance, "Could not retrieve total physical memory via sysctl.")

            # vm_stat for active, inactive, wired, compressed
            vm_stat_output = helpers.run_command("vm_stat", check_shell=True, app_instance=app_instance)
            if vm_stat_output:
                # Attempt to get page size more robustly
                page_size_match = re.search(r'page size of (\d+) bytes', vm_stat_output, re.IGNORECASE)
                page_size_bytes = 4096 # Default to 4KB (4096 bytes)
                if page_size_match:
                    try:
                        page_size_bytes = int(page_size_match.group(1))
                    except ValueError:
                        helpers.log_output(app_instance, f"Warning: Could not parse vm_stat page size value, defaulting to 4KB. Raw match: {page_size_match.group(1)}")
                else:
                    helpers.log_output(app_instance, "Warning: 'Page size of N bytes' not found in vm_stat output, defaulting to 4KB.")

                page_size_gb = page_size_bytes / (1024**3)

                # Use a more generic approach to parse key-value pairs from vm_stat
                vm_stats_dict = {}
                for line in vm_stat_output.splitlines():
                    match = re.match(r'\s*Pages\s+(.+?):\s+(\d+)', line)
                    if match:
                        key = match.group(1).strip().replace(' ', '_').lower()
                        value = int(match.group(2))
                        vm_stats_dict[key] = value

                active_gb = round(vm_stats_dict.get('active', 0) * page_size_gb, 2)
                inactive_gb = round(vm_stats_dict.get('inactive', 0) * page_size_gb, 2)
                wired_gb = round(vm_stats_dict.get('wired_down', 0) * page_size_gb, 2)
                compressed_gb = round(vm_stats_dict.get('occupied_by_physical_pages_that_have_been_decompressed', 0) * page_size_gb, 2)
                
                # Also try to get 'speculative' and 'throttled' if present
                speculative_gb = round(vm_stats_dict.get('speculative', 0) * page_size_gb, 2)
                throttled_gb = round(vm_stats_dict.get('throttled', 0) * page_size_gb, 2)


                html_body += f"<tr><td>Memory Active</td><td>{active_gb} GB</td></tr>"
                html_body += f"<tr><td>Memory Inactive</td><td>{inactive_gb} GB</td></tr>"
                html_body += f"<tr><td>Memory Wired</td><td>{wired_gb} GB</td></tr>"
                html_body += f"<tr><td>Memory Compressed</td><td>{compressed_gb} GB</td></tr>"
                if speculative_gb > 0:
                    html_body += f"<tr><td>Memory Speculative</td><td>{speculative_gb} GB</td></tr>"
                if throttled_gb > 0:
                    html_body += f"<tr><td>Memory Throttled</td><td>{throttled_gb} GB</td></tr>"
                
                # Ensure total_mem_gb is defined before using it
                if 'total_mem_gb' in locals():
                    used_approx = active_gb + inactive_gb + wired_gb + compressed_gb + speculative_gb + throttled_gb
                    available_approx = total_mem_gb - used_approx
                    html_body += f"<tr><td>Memory Used (Approx)</td><td>{round(used_approx, 2)} GB</td></tr>"
                    html_body += f"<tr><td>Memory Available (Approx)</td><td>{round(available_approx, 2)} GB</td></tr>"
                else:
                    html_body += f"<tr><td colspan='2'>Memory Used/Available approximation not possible without Total Memory.</td></tr>"

            # For Swap (memory cached on hard drive) - improved parsing
            swap_info_raw = helpers.run_command("sysctl vm.swapusage", check_shell=True, app_instance=app_instance)
            if swap_info_raw:
                # Regex to specifically capture "total = X.XXM", "used = Y.YYM", "free = Z.ZZM"
                # This pattern is more robust to variations in spacing and optional text like "(encrypted)"
                pattern = r"total = ([\d.]+[MG]?)\s+used = ([\d.]+[MG]?)\s+free = ([\d.]+[MG]?)"
                match = re.search(pattern, swap_info_raw)

                if match:
                    total_swap, used_swap, free_swap = match.groups()
                    html_body += f"<tr><td>Swap Total</td><td>{total_swap}</td></tr>"
                    html_body += f"<tr><td>Swap Used</td><td>{used_swap}</td></tr>"
                    html_body += f"<tr><td>Swap Free</td><td>{free_swap}</td></tr>"
                else:
                    helpers.log_output(app_instance, "Could not parse swapusage output with new regex. Raw output: " + swap_info_raw.strip())
                    html_body += "<tr><td colspan='2'>Could not parse swapusage output.</td></tr>"
            else:
                helpers.log_output(app_instance, "Could not retrieve swapusage info.")

        except Exception as e:
            helpers.log_output(app_instance, f"Error gathering macOS Memory details: {e}")
            html_body += f"<tr><td colspan='2'>Error gathering detailed macOS Memory info.</td></tr>"
    elif sys.platform == "win32":
        try:
            wmic_mem_output = helpers.run_command("wmic ComputerSystem get TotalPhysicalMemory", app_instance=app_instance)
            if wmic_mem_output:
                total_mem_bytes = int(wmic_mem_output.split('\n')[1].strip())
                total_mem_gb = round(total_mem_bytes / (1024**3), 2)
                html_body += f"<tr><td>Total Physical Memory</td><td>{total_mem_gb} GB</td></tr>"

            wmic_os_mem_output = helpers.run_command("wmic OS get FreePhysicalMemory,TotalVisibleMemorySize,FreeVirtualMemory,TotalVirtualMemorySize", app_instance=app_instance)
            if wmic_os_mem_output:
                lines = wmic_os_mem_output.strip().split('\n')
                if len(lines) > 1:
                    headers = [h.strip() for h in lines[0].split()]
                    values = [v.strip() for v in lines[1].split()]
                    mem_dict = dict(zip(headers, values))
                    
                    html_body += f"<tr><td>Free Physical Memory</td><td>{round(int(mem_dict.get('FreePhysicalMemory', 0)) / 1024, 2)} MB</td></tr>"
                    html_body += f"<tr><td>Total Visible Memory</td><td>{round(int(mem_dict.get('TotalVisibleMemorySize', 0)) / 1024, 2)} MB</td></tr>"
                    html_body += f"<tr><td>Free Virtual Memory</td><td>{round(int(mem_dict.get('FreeVirtualMemory', 0)) / 1024, 2)} MB</td></tr>"
                    html_body += f"<tr><td>Total Virtual Memory</td><td>{round(int(mem_dict.get('TotalVirtualMemorySize', 0)) / 1024, 2)} MB</td></tr>"
        except Exception as e:
            helpers.log_output(app_instance, f"Error gathering Windows Memory details: {e}")
            html_body += f"<tr><td colspan='2'>Error gathering detailed Windows Memory info.</td></tr>"
    html_body += """</table>"""

    # --- Storage Information ---
    html_body += "<h2>Storage Information</h2><table><tr><th>Drive/Volume</th><th>Size</th><th>Used</th><th>Available</th><th>Filesystem</th><th>Mount Point</th><th>Serial (if available)</th></tr>"
    if sys.platform == "darwin":
        parsed_disks = []
        try: # This is the try block for plistlib.loads below
            disk_info_plist_str = helpers.run_command("diskutil list -plist", check_shell=True, app_instance=app_instance)
            if disk_info_plist_str:
                try: # This inner try is for plistlib.loads
                    disk_plist = plistlib.loads(disk_info_plist_str) # No .encode('utf-8') needed if already bytes
                    all_disks_and_partitions = disk_plist.get('AllDisksAndPartitions', [])
                    
                    for disk_entry in all_disks_and_partitions:
                        # Defensive check: ensure disk_entry is actually a dictionary
                        if not isinstance(disk_entry, dict):
                            helpers.log_output(app_instance, f"Warning: Skipping non-dictionary disk entry: {type(disk_entry)} - {disk_entry}")
                            continue # Skip to next item in loop

                        disk_name = disk_entry.get('DeviceIdentifier', 'N/A')
                        disk_size_bytes = disk_entry.get('Size', 0)
                        disk_size_gb = round(disk_size_bytes / (1024**3), 2)
                        disk_serial = "N/A"

                        if disk_entry.get('Product'):
                            # Try to get serial for the *physical* disk
                            # Combine SPNVMeDataType and SPSerialATADataType for modern Macs
                            serial_output = helpers.run_command(f"system_profiler SPNVMeDataType SPSerialATADataType | grep \"{disk_entry['Product']}\" -B 5 | grep \"Serial Number:\"", check_shell=True, app_instance=app_instance)
                            if serial_output:
                                serial_match = re.search(r'Serial Number: (.+)', serial_output)
                                if serial_match:
                                    disk_serial = serial_match.group(1).strip()
                            else:
                                helpers.log_output(app_instance, f"Could not get serial for {disk_name} via system_profiler.")
                        
                        parsed_disks.append(DiskInfo(
                            name=disk_name,
                            type="Physical Disk",
                            size_gb=disk_size_gb,
                            used="N/A", available="N/A", # These are for logical volumes
                            filesystem="N/A", mount_point="N/A",
                            serial=disk_serial,
                            volume_name="N/A", device_identifier=disk_name # Populate other fields as N/A for physical
                        ))

                        if 'Partitions' in disk_entry and isinstance(disk_entry['Partitions'], list):
                            for partition in disk_entry['Partitions']:
                                # Defensive check: ensure partition is a dictionary
                                if not isinstance(partition, dict):
                                    helpers.log_output(app_instance, f"Warning: Skipping non-dictionary partition: {type(partition)} - {partition}")
                                    continue
                                
                                part_name = partition.get('VolumeName', partition.get('DeviceIdentifier', 'N/A'))
                                part_size_bytes = partition.get('Size', 0)
                                part_size_gb = round(part_size_bytes / (1024**3), 2)
                                part_fs = partition.get('FilesystemType', 'N/A')
                                part_mount_point = partition.get('MountPoint', 'N/A')

                                used = "N/A"
                                avail = "N/A"
                                if part_mount_point and part_mount_point != "N/A":
                                    df_output = helpers.run_command(f"df -h '{part_mount_point}'", check_shell=True, app_instance=app_instance)
                                    if df_output and len(df_output.splitlines()) > 1:
                                        df_parts = df_output.splitlines()[1].split()
                                        if len(df_parts) > 3:
                                            used = df_parts[2]
                                            avail = df_parts[3]

                                parsed_disks.append(DiskInfo(
                                    name=part_name,
                                    type="Partition",
                                    size_gb=part_size_gb,
                                    used=used, available=avail,
                                    filesystem=part_fs, mount_point=part_mount_point,
                                    serial="N/A", # Partitions usually don't have separate serials
                                    volume_name=partition.get('VolumeName'), device_identifier=partition.get('DeviceIdentifier')
                                ))

                except plistlib.InvalidFileException: # THIS IS THE EXCEPT BLOCK at Line 255
                    helpers.log_output(app_instance, f"Error: diskutil list -plist output not valid. Raw output snippet: {disk_info_plist_str[:500]}...")
                    html_body += f"<tr><td colspan='7'>Error parsing diskutil output. Raw data snippet: <pre>{disk_info_plist_str[:500]}</pre></td></tr>"
                except Exception as e:
                    helpers.log_output(app_instance, f"Unexpected error parsing diskutil list: {e}")
                    html_body += f"<tr><td colspan='7'>Unexpected error parsing diskutil list.</td></tr>"

            if parsed_disks:
                for d in parsed_disks:
                    html_body += f"<tr><td>{d.name} ({d.type})</td><td>{d.size_gb} GB</td><td>{d.used}</td><td>{d.available}</td><td>{d.filesystem}</td><td>{d.mount_point}</td><td>{d.serial}</td></tr>"
            else:
                html_body += "<p>No storage devices found or processed.</p>"

        except Exception as e:
            helpers.log_output(app_instance, f"Error gathering macOS Storage details: {e}")
            html_body += f"<tr><td colspan='7'>Error gathering detailed macOS Storage info.</td></tr>"
    elif sys.platform == "win32":
        try:
            wmic_disk_output = helpers.run_command("wmic diskdrive get Caption,SerialNumber,Size /format:list", app_instance=app_instance)
            if wmic_disk_output:
                html_body += "<tr><th colspan='7'>Physical Disk Drives</th></tr>"
                current_disk = {}
                for line in wmic_disk_output.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        current_disk[key.strip()] = value.strip()
                    elif not line.strip() and current_disk:
                        size_gb = round(int(current_disk.get('Size', 0)) / (1024**3), 2)
                        html_body += f"<tr><td>{current_disk.get('Caption', 'N/A')}</td><td>{size_gb} GB</td><td>N/A</td><td>N/A</td><td>N/A</td><td>N/A</td><td>{current_disk.get('SerialNumber', 'N/A')}</td></tr>"
                        current_disk = {}
                if current_disk:
                    size_gb = round(int(current_disk.get('Size', 0)) / (1024**3), 2)
                    html_body += f"<tr><td>{current_disk.get('Caption', 'N/A')}</td><td>{size_gb} GB</td><td>N/A</td><td>N/A</td><td>N/A</td><td>N/A</td><td>{current_disk.get('SerialNumber', 'N/A')}</td></tr>"

            wmic_volume_output = helpers.run_command("wmic logicaldisk get Caption,Freespace,Size,FileSystem /format:list", app_instance=app_instance)
            if wmic_volume_output:
                html_body += "<tr><th colspan='7'>Logical Disk Volumes</th></tr>"
                current_volume = {}
                for line in wmic_volume_output.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        current_volume[key.strip()] = value.strip()
                    elif not line.strip() and current_volume:
                        size_gb = round(int(current_volume.get('Size', 0)) / (1024**3), 2)
                        free_gb = round(int(current_volume.get('FreeSpace', 0)) / (1024**3), 2)
                        used_gb = round(size_gb - free_gb, 2)
                        html_body += f"<tr><td>{current_volume.get('Caption', 'N/A')}</td><td>{size_gb} GB</td><td>{used_gb} GB</td><td>{free_gb} GB</td><td>{current_volume.get('FileSystem', 'N/A')}</td><td>N/A</td><td>N/A</td></tr>"
                        current_volume = {}
                if current_volume:
                    size_gb = round(int(current_volume.get('Size', 0)) / (1024**3), 2)
                    free_gb = round(int(current_volume.get('FreeSpace', 0)) / (1024**3), 2)
                    used_gb = round(size_gb - free_gb, 2)
                    html_body += f"<tr><td>{current_volume.get('Caption', 'N/A')}</td><td>{size_gb} GB</td><td>{used_gb} GB</td><td>{free_gb} GB</td><td>{current_volume.get('FileSystem', 'N/A')}</td><td>N/A</td><td>N/A</td></tr>"

        except Exception as e:
            helpers.log_output(app_instance, f"Error gathering Windows Storage details: {e}")
            html_body += f"<tr><td colspan='7'>Error gathering detailed Windows Storage info.</td></tr>"
    html_body += """</table>"""

    # --- Connected Devices (USB, Camera, Bluetooth) ---
    html_body += "<h2>Connected Devices</h2>"
    if sys.platform == "darwin":
        # The main try block for macOS connected devices
        try:
            # USB Devices
            html_body += "<h3>USB Devices</h3>"
            usb_info_plist_bytes = helpers.run_command("system_profiler -xml SPUSBDataType", check_shell=True, app_instance=app_instance)
            if usb_info_plist_bytes:
                # MODIFIED: Call the new _process_sp_device_data
                usb_devices_data = _process_sp_device_data(
                    usb_info_plist_bytes,
                    'SPUSBDataType',
                    app_instance
                )
                
                if usb_devices_data:
                    html_body += "<table><tr><th>Name</th><th>Manufacturer</th><th>Product ID</th><th>Vendor ID</th><th>Serial Number</th><th>Location ID</th></tr>"
                    for dev in usb_devices_data:
                        html_body += (f"<tr><td>{dev.get('_name', 'N/A')}</td><td>{dev.get('manufacturer', 'N/A')}</td>"
                                      f"<td>{dev.get('product_id', 'N/A')}</td><td>{dev.get('vendor_id', 'N/A')}</td>"
                                      f"<td>{dev.get('serial_num', 'N/A')}</td><td>{dev.get('location_id', 'N/A')}</td></tr>")
                    html_body += "</table>"
                else:
                    html_body += "<p>No USB devices found or could not retrieve information.</p>"
            else:
                helpers.log_output(app_instance, "Could not retrieve USB device information via system_profiler.")
                html_body += "<p>Could not retrieve USB device information.</p>"

            # Camera
            html_body += "<h3>Camera Information</h3>"
            camera_info_plist_bytes = helpers.run_command("system_profiler -xml SPCameraDataType", check_shell=True, app_instance=app_instance)
            if camera_info_plist_bytes:
                # MODIFIED: Call the new _process_sp_device_data
                camera_devices_data = _process_sp_device_data(
                    camera_info_plist_bytes,
                    'SPCameraDataType',
                    app_instance
                )

                if camera_devices_data:
                    html_body += "<table><tr><th>Name</th><th>Manufacturer</th><th>Model ID</th><th>Unique ID</th></tr>"
                    for cam_dict in camera_devices_data:
                        html_body += (f"<tr><td>{cam_dict.get('_name', 'N/A')}</td><td>{cam_dict.get('manufacturer', 'N/A')}</td>"
                                      f"<td>{cam_dict.get('model_id', 'N/A')}</td><td>{cam_dict.get('unique_id', 'N/A')}</td></tr>")
                    html_body += "</table>"
                else:
                    html_body += "<p>No camera found or could not retrieve information.</p>"
            else:
                helpers.log_output(app_instance, "Could not retrieve Camera information via system_profiler.")
                html_body += "<p>No camera found or could not retrieve information.</p>"

            # Bluetooth
            html_body += "<h3>Bluetooth Information</h3>"
            bluetooth_info_plist_bytes = helpers.run_command("system_profiler -xml SPBluetoothDataType", check_shell=True, app_instance=app_instance)
            if bluetooth_info_plist_bytes:
                # MODIFIED: Call the new _process_sp_device_data
                bluetooth_devices_data = _process_sp_device_data(
                    bluetooth_info_plist_bytes,
                    'SPBluetoothDataType',
                    app_instance
                )
                
                if bluetooth_devices_data:
                    # Updated HTML table structure for Bluetooth for consistency
                    html_body += "<table><tr><th>Name</th><th>Manufacturer</th><th>Vendor ID</th><th>Product ID</th><th>Address</th><th>Device Address</th><th>Class of Service</th><th>Class of Device</th><th>Connected</th></tr>"
                    for bt_item in bluetooth_devices_data:
                        html_body += (f"<tr><td>{bt_item.get('_name', 'N/A')}</td><td>{bt_item.get('manufacturer', 'N/A')}</td>"
                                      f"<td>{bt_item.get('vendor_id', 'N/A')}</td><td>{bt_item.get('product_id', 'N/A')}</td>"
                                      f"<td>{bt_item.get('address', 'N/A')}</td><td>{bt_item.get('device_address', 'N/A')}</td>"
                                      f"<td>{bt_item.get('device_class_of_service', 'N/A')}</td><td>{bt_item.get('class_of_device', 'N/A')}</td>"
                                      f"<td>{bt_item.get('is_connected', 'N/A')}</td></tr>")
                    html_body += "</table>"
                else:
                    html_body += "<p>No Bluetooth devices found or could not retrieve information.</p>"
            else:
                helpers.log_output(app_instance, "Could not retrieve Bluetooth information via system_profiler.")
                html_body += "<p>No Bluetooth devices found or could not retrieve information.</p>"


        except Exception as e: # This is the except block for the try at line 317
            helpers.log_output(app_instance, f"Error gathering macOS Connected Devices details: {e}")
            html_body += f"<p>Error gathering detailed macOS Connected Devices info: {e}</p>"
    elif sys.platform == "win32":
        html_body += "<h3>USB Devices (Windows)</h3>"
        usb_output = helpers.run_command("wmic path Win32_USBHub get DeviceID,PNPDeviceID,Description /format:list", app_instance=app_instance)
        if usb_output:
            html_body += "<pre>" + usb_output + "</pre>"
        else:
            html_body += "<p>Could not retrieve USB device information.</p>"
        
        html_body += "<h3>Camera/Webcam (Windows)</h3>"
        camera_output = helpers.run_command("wmic path Win32_PnPEntity where \"ConfigManagerErrorCode = 0 and (Name like '%camera%' or Name like '%webcam%')\" get Name,DeviceID /format:list", app_instance=app_instance)
        if camera_output:
            html_body += "<pre>" + camera_output + "</pre>"
        else:
            html_body += "<p>No camera/webcam found or could not retrieve information.</p>"

        html_body += "<h3>Bluetooth Devices (Windows)</h3>"
        bluetooth_output = helpers.run_command("wmic path Win32_PnPEntity where \"ConfigManagerErrorCode = 0 and (Name like '%bluetooth%')\" get Name,DeviceID /format:list", app_instance=app_instance)
        if bluetooth_output:
            html_body += "<pre>" + bluetooth_output + "</pre>"
        else:
            html_body += "<p>No Bluetooth devices found or could not retrieve information.</p>"
    html_body += """<p>For more detailed interpretations or comparisons, specialized benchmarking tools are required.</p>"""

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "SYSINFO_Report.html", 
        "System Information Report", 
        html_body,
        browser_preference=browser_preference
    )

# --- Remaining (Existing) Diagnostic Functions - NO CHANGES HERE ---

def local_accounts(app_instance, helpers, browser_preference="System Default"):
    """Gathers and reports local user accounts and administrator status."""
    helpers.log_output(app_instance, "\nChecking for Computer Accounts...")
    
    html_body = ""

    if sys.platform == "win32":
        helpers.log_output(app_instance, "Gathering Windows local accounts and profiles...")
        local_users_output = helpers.run_command("net user", check_shell=True, app_instance=app_instance)
        admin_group_output = helpers.run_command("net localgroup Administrators", check_shell=True, app_instance=app_instance)
        
        html_body += "<h3>Local Users (basic output from 'net user'):</h3>"
        if local_users_output:
            html_body += f"<pre>{local_users_output}</pre>"
        html_body += "<h3>Local Administrators (basic output from 'net localgroup Administrators'):</h3>"
        if admin_group_output:
            html_body += f"<pre>{admin_group_output}</pre>"

    elif sys.platform == "darwin":
        helpers.log_output(app_instance, "Gathering macOS local accounts and admin group membership...")
        
        users_list = helpers.run_command("dscl . -list /Users", check_shell=True, app_instance=app_instance)
        if users_list:
            html_body += "<h3>Local User Accounts:</h3><table><tr><th>Username</th><th>Is Admin</th></tr>"
            admin_members_output = helpers.run_command("dscl . -read /Groups/admin GroupMembership", check_shell=True, app_instance=app_instance)
            admin_members = []
            if admin_members_output and "GroupMembership:" in admin_members_output:
                admin_members = admin_members_output.split("GroupMembership:")[1].strip().split()
            
            for user in users_list.strip().split('\n'):
                is_admin = "Yes" if user.strip() in admin_members else "No"
                html_body += f"<tr><td>{user.strip()}</td><td>{is_admin}</td></tr>"
            html_body += "</table>"
        
        html_body += "<h3>User Home Directories:</h3><table><tr><th>Path</th></tr>"
        home_dirs = helpers.run_command("ls /Users", check_shell=True, app_instance=app_instance)
        if home_dirs:
            for d in home_dirs.strip().split('\n'):
                html_body += f"<tr><td>/Users/{d.strip()}</td></tr>"
        html_body += "</table>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "UserAccountsAndLocalAdminsReport.html", 
        "User Accounts and Local Admins Report", 
        html_body,
        browser_preference=browser_preference
    )

def check_malicious_scripts(app_instance, helpers, browser_preference="System Default"):
    """Scans for potentially malicious running scripts based on keywords."""
    helpers.log_output(app_instance, "\nRunning Malicious Script Check....")
    
    html_body = """
<p>This report identifies potentially malicious scripts running on the system by checking for suspicious keywords in process command lines.</p>
<table><tr><th>PID</th><th>User</th><th>Command Line</th></tr>
"""

    if sys.platform == "win32":
        helpers.log_output(app_instance, "Scanning for suspicious PowerShell processes on Windows...")
        script_check_results = helpers.run_command(
            r"powershell.exe -Command \"Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match 'http|https|base64|powershell -e|pwsh -e' } | Select-Object ProcessId, Name, CommandLine | ConvertTo-Json\"", 
            check_shell=True, app_instance=app_instance
        )
        if script_check_results:
            try:
                processes = json.loads(script_check_results)
                for proc in processes:
                    html_body += f"<tr><td>{proc.get('ProcessId', 'N/A')}</td><td>{proc.get('Name', 'N/A')}</td><td>{proc.get('CommandLine', 'N/A')}</td></tr>"
                html_body += "</table>"
            except json.JSONDecodeError:
                helpers.log_output(app_instance, "Error parsing PowerShell output for malicious script check.")
                html_body += "<tr><td colspan='3' style='color: red;'>Error parsing suspicious script check results.</td></tr></table>"
        else:
            html_body += "<tr><td colspan='3' style='color: green; font-weight: bold;'>No suspicious PowerShell activity detected.</td></tr></table>"

    elif sys.platform == "darwin":
        helpers.log_output(app_instance, "Scanning for suspicious processes on macOS using 'ps aux'...")
        # Common suspicious patterns: base64 encoded commands, direct downloads, unexpected shell scripts
        suspicious_patterns = r"(curl|wget|python -c|perl -e|php -r).*?(http|https)|(base64 -D)"
        
        all_processes = helpers.run_command("ps aux", check_shell=True, app_instance=app_instance)
        if all_processes:
            found_suspicious = False
            for line in all_processes.strip().split('\n')[1:]:
                if re.search(suspicious_patterns, line, re.IGNORECASE):
                    parts = line.strip().split(None, 10)
                    if len(parts) >= 11:
                        pid = parts[1]
                        user = parts[0]
                        cmd = " ".join(parts[10:])
                        html_body += f"<tr><td>{pid}</td><td>{user}</td><td>{cmd}</td></tr>"
                        found_suspicious = True
            html_body += "</table>"
            
            if not found_suspicious:
                html_body = html_body.replace("</table>", "<tr><td colspan='3' style='color: green; font-weight: bold;'>No suspicious activity detected on macOS.</td></tr></table>")
        else:
            html_body += "<tr><td colspan='3'>Could not retrieve process list.</td></tr></table>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        f"MaliciousScriptsReport_{datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')}.html", 
        "Potentially Malicious Running Scripts Report", 
        html_body,
        browser_preference=browser_preference
    )

def running_process(app_instance, helpers, browser_preference="System Default"):
    """Gathers and reports running processes and services."""
    helpers.log_output(app_instance, "\nStarting Running Process Report....")
    
    html_body = ""

    # Running Processes
    html_body += "<h2>Running Processes</h2><table><tr><th>Name</th><th>PID</th><th>User</th></tr>"
    if sys.platform == "win32":
        processes_output = helpers.run_command(r"powershell.exe -Command \"Get-Process | Select-Object ProcessName, Id, @{Name='UserName';Expression={$_.Owner}}\"", app_instance=app_instance)
        if processes_output:
            for line in processes_output.strip().split('\n')[3:]:
                parts = line.strip().split(None, 2)
                if len(parts) == 3:
                    name = parts[0]
                    pid = parts[1]
                    user = parts[2]
                    html_body += f"<tr><td>{name}</td><td>{pid}</td><td>{user}</td></tr>"
        else:
            html_body += "<tr><td colspan='3'>Could not retrieve Windows processes.</td></tr>"
    elif sys.platform == "darwin":
        processes_output = helpers.run_command("ps aux", check_shell=True, app_instance=app_instance)
        if processes_output:
            for line in processes_output.strip().split('\n')[1:]:
                parts = line.strip().split(None, 10)
                if len(parts) >= 11:
                    user = parts[0]
                    pid = parts[1]
                    cmd = " ".join(parts[10:])
                    html_body += f"<tr><td>{cmd}</td><td>{pid}</td><td>{user}</td></tr>"
        else:
            html_body += "<tr><td colspan='3'>Could not retrieve macOS processes.</td></tr>"
    html_body += "</table>"

    # Services (Windows-only, for macOS will be LaunchDaemons/Agents)
    html_body += "<h2>Services and Their Status</h2><table><tr><th>Display Name</th><th>Status</th></tr>"
    if sys.platform == "win32":
        services_output = helpers.run_command(r"powershell.exe -Command \"Get-Service | Select-Object DisplayName, Status\"", app_instance=app_instance)
        if services_output:
            for line in services_output.strip().split('\n')[3:]:
                parts = line.strip().rsplit(None, 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    status = parts[1].strip()
                    html_body += f"<tr><td>{name}</td><td>{status}</td></tr>"
        else:
            html_body += "<tr><td colspan='2'>Could not retrieve Windows services.</td></tr>"
    elif sys.platform == "darwin":
        helpers.log_output(app_instance, "For macOS, services are typically managed via LaunchDaemons/Agents.")
        launch_daemons = helpers.run_command("sudo launchctl list", check_shell=True, app_instance=app_instance)
        html_body += "<tr><td colspan='2'><b>macOS LaunchDaemons/Agents (partial via `launchctl list`):</b></td></tr>"
        if launch_daemons:
            html_body += f"<tr><td colspan='2'><pre>{launch_daemons}</pre></td></tr>"
        else:
            html_body += "<tr><td colspan='2'>Could not retrieve LaunchDaemons/Agents.</td></tr>"
    html_body += "</table>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "RunningProcessesAndServices.html", 
        "Running Processes and Services Report", 
        html_body,
        browser_preference=browser_preference
    )

def netstat_connections(app_instance, helpers, browser_preference="System Default"):
    """Gathers and reports active network connections (netstat -an)."""
    helpers.log_output(app_instance, "\nStarting Netstat Report...")
    
    html_body = """<table><tr><th>Protocol</th><th>Local Address</th><th>Foreign Address</th><th>State</th></tr>"""
    
    netstat_output = helpers.run_command("sudo netstat -an", check_shell=True, app_instance=app_instance)
    if netstat_output:
        for line in netstat_output.strip().split('\n'):
            if line.strip().startswith(('TCP', 'UDP', 'tcp', 'udp')):
                fields = line.strip().split()
                if len(fields) >= 4:
                    protocol = fields[0]
                    local_address = fields[1]
                    foreign_address = fields[2]
                    state = fields[3] if len(fields) > 3 else "N/A"
                    html_body += f"<tr><td>{protocol}</td><td>{local_address}</td><td>{foreign_address}</td><td>{state}</td></tr>"
        if not html_body.strip().endswith("</tr>"):
            html_body += "<tr><td colspan='4'>No network connections found or permission denied. Try running with elevated privileges.</td></tr>"
    else:
        html_body += "<tr><td colspan='4'>Could not retrieve Netstat output. Try running with elevated privileges.</td></tr>"

    html_body += """</table>"""

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "NetstatReport.html", 
        "Netstat Report", 
        html_body,
        browser_preference=browser_preference
    )

def scheduled_tasks(app_instance, helpers, browser_preference="System Default"):
    """
    Gathers and reports scheduled tasks on macOS (LaunchDaemons/Agents, Cron jobs).
    """
    helpers.log_output(app_instance, "\nRunning Scheduled Task Report....")
    
    html_body = "<h2>Scheduled Tasks Report</h2>"

    if sys.platform == "darwin":
        # --- LaunchDaemons (System-wide, often requires sudo) ---
        html_body += "<h3>macOS LaunchDaemons (System-wide Tasks)</h3>"
        helpers.log_output(app_instance, "Gathering LaunchDaemons from /Library/LaunchDaemons/ and /System/Library/LaunchDaemons/...")
        daemon_paths = ["/Library/LaunchDaemons/", "/System/Library/LaunchDaemons/"] 
        
        daemon_data = []
        for path_dir in daemon_paths:
            helpers.log_output(app_instance, f"Checking LaunchDaemon directory: {path_dir}")
            if os.path.exists(path_dir):
                helpers.log_output(app_instance, f"Directory exists: {path_dir}")
                list_output = helpers.run_command(f"sudo ls {path_dir}", check_shell=True, app_instance=app_instance) 
                if list_output:
                    helpers.log_output(app_instance, f"Successfully listed files in {path_dir}. Processing {len(list_output.strip().splitlines())} files.")
                    for filename in list_output.strip().splitlines(): 
                        if filename.endswith(".plist"):
                            plist_file_path = os.path.join(path_dir, filename)
                            helpers.log_output(app_instance, f"  Attempting to read plist: {plist_file_path}")
                            data = helpers.read_plist_file(plist_file_path, app_instance=app_instance)
                            if data:
                                program_arg = "N/A"
                                if "Program" in data:
                                    program_arg = data["Program"]
                                elif "ProgramArguments" in data:
                                    program_arg = " ".join(map(str, data["ProgramArguments"]))
                                
                                daemon_data.append({
                                    "Source": plist_file_path,
                                    "Label": data.get("Label", "N/A"),
                                    "Program": program_arg,
                                    "RunAtLoad": data.get("RunAtLoad", False),
                                    "StartInterval": data.get("StartInterval", "N/A"),
                                    "StartCalendarInterval": data.get("StartCalendarInterval", "N/A"),
                                    "KeepAlive": data.get("KeepAlive", False)
                                })
                                helpers.log_output(app_instance, f"  ✅ Successfully processed {plist_file_path}.")
                            else:
                                helpers.log_output(app_instance, f"  ❌ Could not read content of {plist_file_path} (Permission denied or invalid format).")
                        else:
                            helpers.log_output(app_instance, f"  Skipping non-plist file: {filename}")
                else:
                    helpers.log_output(app_instance, f"❌ Could not list LaunchDaemons in {path_dir} (Command failed or permission denied for `sudo ls`).")
            else:
                helpers.log_output(app_instance, f"❌ Directory does not exist (LaunchDaemons): {path_dir}")
        
        if daemon_data:
            html_body += "<table><tr><th>Source</th><th>Label</th><th>Program/Command</th><th>Run At Load</th><th>Interval (sec)</th><th>Calendar Interval</th><th>Keep Alive</th></tr>"
            for item in daemon_data:
                html_body += f"<tr><td>{item['Source']}</td><td>{item['Label']}</td><td><pre>{item['Program']}</pre></td><td>{item['RunAtLoad']}</td><td>{item['StartInterval']}</td><td>{item['StartCalendarInterval']}</td><td>{item['KeepAlive']}</td></tr>"
            html_body += "</table>"
        else:
            html_body += "<p>No LaunchDaemons found or processed. Some may require elevated privileges to list or read contents.</p>"


        # --- LaunchAgents (User-specific and System-wide for all users) ---
        html_body += "<h3>macOS LaunchAgents (User-Specific and All-User Tasks)</h3>"
        helpers.log_output(app_instance, "Gathering LaunchAgents from ~/Library/LaunchAgents/ and /Library/LaunchAgents/...")
        agent_paths = [os.path.expanduser("~/Library/LaunchAgents/"), "/Library/LaunchAgents/"]
        
        agent_data = []
        for path_dir in agent_paths:
            helpers.log_output(app_instance, f"Checking LaunchAgent directory: {path_dir}")
            if os.path.exists(path_dir):
                helpers.log_output(app_instance, f"Directory exists: {path_dir}")
                # Use sudo for /Library/LaunchAgents/, but not for user's ~/Library/LaunchAgents/
                command_to_list = f"sudo ls {path_dir}" if path_dir == "/Library/LaunchAgents/" else f"ls {path_dir}"
                list_output = helpers.run_command(command_to_list, check_shell=True, app_instance=app_instance) 
                if list_output:
                    helpers.log_output(app_instance, f"Successfully listed files in {path_dir}. Processing {len(list_output.strip().splitlines())} files.")
                    for filename in list_output.strip().splitlines():
                        if filename.endswith(".plist"):
                            plist_file_path = os.path.join(path_dir, filename)
                            helpers.log_output(app_instance, f"  Attempting to read plist: {plist_file_path}")
                            data = helpers.read_plist_file(plist_file_path, app_instance=app_instance)
                            if data:
                                program_arg = "N/A"
                                if "Program" in data:
                                    program_arg = data["Program"]
                                elif "ProgramArguments" in data:
                                    program_arg = " ".join(map(str, data["ProgramArguments"]))
                                
                                agent_data.append({
                                    "Source": plist_file_path,
                                    "Label": data.get("Label", "N/A"),
                                    "Program": program_arg,
                                    "RunAtLoad": data.get("RunAtLoad", False),
                                    "StartInterval": data.get("StartInterval", "N/A"),
                                    "StartCalendarInterval": data.get("StartCalendarInterval", "N/A"),
                                    "KeepAlive": data.get("KeepAlive", False)
                                })
                                helpers.log_output(app_instance, f"  ✅ Successfully processed {plist_file_path}.")
                            else:
                                helpers.log_output(app_instance, f"  ❌ Could not read content of {plist_file_path} (Permission denied or invalid format).")
                        else:
                            helpers.log_output(app_instance, f"  Skipping non-plist file: {filename}")
                else:
                    helpers.log_output(app_instance, f"❌ Could not list LaunchAgents in {path_dir} (Command failed or permission denied for `{command_to_list}`).")
            else:
                helpers.log_output(app_instance, f"❌ Directory does not exist (LaunchAgents): {path_dir}")

        if agent_data:
            html_body += "<table><tr><th>Source</th><th>Label</th><th>Program/Command</th><th>Run At Load</th><th>Interval (sec)</th><th>Calendar Interval</th><th>Keep Alive</th></tr>"
            for item in agent_data:
                html_body += f"<tr><td>{item['Source']}</td><td>{item['Label']}</td><td><pre>{item['Program']}</pre></td><td>{item['RunAtLoad']}</td><td>{item['StartInterval']}</td><td>{item['StartCalendarInterval']}</td><td>{item['KeepAlive']}</td></tr>"
            html_body += "</table>"
        else:
            html_body += "<p>No LaunchAgents found or processed.</p>"

        # --- Cron Jobs (Traditional Unix Scheduling) ---
        html_body += "<h3>macOS Cron Jobs</h3>"
        helpers.log_output(app_instance, "Gathering current user cron jobs via `crontab -l`...")
        cron_output = helpers.run_command("crontab -l", check_shell=True, app_instance=app_instance) 
        if cron_output:
            html_body += "<h4>Current User Crontab:</h4>"
            html_body += f"<pre>{cron_output}</pre>"
        else:
            helpers.log_output(app_instance, "No cron jobs found for current user or `crontab -l` command failed to retrieve output.")
            html_body += "<p>No cron jobs found for current user.</p>" 

        # System-wide cron directories (often contain scripts, not direct cron entries)
        html_body += "<h4>System-wide Cron Directories and Files:</h4>"
        cron_system_paths = ["/etc/crontab", "/etc/cron.d/", "/etc/cron.daily/", "/etc/cron.hourly/", "/etc/cron.monthly/", "/etc/cron.weekly/"]
        found_system_cron_info = False
        for cpath in cron_system_paths:
            helpers.log_output(app_instance, f"Checking system cron directory/file: {cpath}")
            if os.path.exists(cpath):
                helpers.log_output(app_instance, f"Directory exists: {cpath}")
                if os.path.isdir(cpath):
                    scripts_in_dir = helpers.run_command(f"sudo ls -l {cpath}", check_shell=True, app_instance=app_instance) 
                    if scripts_in_dir:
                        helpers.log_output(app_instance, f"Successfully listed scripts in {cpath}.")
                        html_body += f"<h5>Contents of directory: {cpath}</h5><pre>{scripts_in_dir}</pre>" 
                        found_system_cron_info = True
                    else:
                        helpers.log_output(app_instance, f"❌ Could not list contents of directory {cpath} (Command failed or permission denied for `sudo ls -l`).")
                elif os.path.isfile(cpath):
                    file_content = helpers.run_command(f"sudo cat {cpath}", check_shell=True, app_instance=app_instance) 
                    if file_content:
                        helpers.log_output(app_instance, f"Successfully read content of {cpath}.")
                        html_body += f"<h5>Content of file: {cpath}</h5><pre>{file_content}</pre>" 
                        found_system_cron_info = True
                    else:
                        helpers.log_output(app_instance, f"❌ Could not read content of {cpath} (Command failed or permission denied for `sudo cat`).")
            else:
                helpers.log_output(app_instance, f"❌ Cron directory/file does not exist: {cpath}")
        if not found_system_cron_info:
            html_body += "<p>No system-wide cron scripts or crontab files found in standard locations or permission denied.</p>"
            helpers.log_output(app_instance, "No system-wide cron information found or accessible.")

    else:
        html_body += "<p>Scheduled tasks reporting for Windows/Linux is different and not yet fully implemented here. (Only basic macOS scaffolding).</p>"

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "ScheduledTasksReport.html", 
        "Scheduled Tasks Report", 
        html_body,
        browser_preference=browser_preference
    )

# --- Main execution for testing ---
if __name__ == "__main__":
    # Instantiate mock objects
    mock_app = MockAppInstance()
    mock_helpers = Helpers(mock_app)

    # Call the sys_info function with mock objects
    sys_info(mock_app, mock_helpers, browser_preference="System Default")

    print("\n--- Mock Log Output ---")
    for msg in mock_app.log_messages:
        print(msg)
    print("-----------------------")
    print(f"Check your desktop for 'TEST_COMPUTER IRIS REPORTS/SYSINFO_Report.html'")
