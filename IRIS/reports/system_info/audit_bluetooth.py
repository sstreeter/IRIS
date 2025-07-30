import sys
import subprocess
import plistlib
import requests
import os
import datetime
import re

# --- Configuration ---
OUI_FILE_PATH = "oui.txt"
OUI_FILE_MAX_AGE_DAYS = 60
OUI_URL = "https://standards-oui.ieee.org/oui/oui.txt"
VENDOR_ID_MAP = {
    "0x004C": {"name": "Apple, Inc.", "slug": "apple"},
    "0x046D": {"name": "Logitech", "slug": "logitech"},
    "0x0006": {"name": "Microsoft", "slug": "microsoft"},
}

# --- Helper Functions for Vendor Lookup ---
def download_oui_file():
    print(f"   ℹ️ Downloading fresh OUI file from IEEE...")
    try:
        response = requests.get(OUI_URL, timeout=15)
        response.raise_for_status()
        with open(OUI_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"   ✅ Download successful.")
        return True
    except requests.RequestException as e:
        print(f"   ❌ Download failed: {e}")
        return False

def parse_local_oui_file(mac_address):
    try:
        normalized_mac_oui = mac_address.replace(":", "").replace("-", "").upper()[:6]
        with open(OUI_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                if '(hex)' in line:
                    file_oui = line.split('(hex)')[0].replace('-', '').strip()
                    if normalized_mac_oui == file_oui:
                        return line.split('(hex)')[1].strip()
    except (FileNotFoundError, AttributeError):
        return None
    return None

def get_vendor_from_local_fallback(mac_address):
    file_exists = os.path.exists(OUI_FILE_PATH)
    needs_download = not file_exists
    if file_exists:
        file_age = datetime.datetime.now().timestamp() - os.path.getmtime(OUI_FILE_PATH)
        if file_age > (OUI_FILE_MAX_AGE_DAYS * 86400):
            print("   ℹ️ Local OUI file is stale.")
            needs_download = True
    if needs_download and not download_oui_file() and not file_exists:
        return "Local lookup failed"
    return parse_local_oui_file(mac_address) or "Vendor not found in local file"

def get_mac_vendor(mac_address):
    try:
        response = requests.get(f"https://api.macvendors.com/{mac_address}", timeout=3)
        if response.status_code == 200:
            return response.text
    except requests.RequestException:
        pass
    print(f"   ℹ️ API lookup failed for {mac_address}. Using local fallback.")
    return get_vendor_from_local_fallback(mac_address)

# --- Helper Function for Printing Device Info ---
def print_device_details(name, properties):
    """Processes and prints the details for a single device."""
    print(f"\n🔷 Device Name: {name}")
    vendor_id = properties.get('device_vendorID') or properties.get('vendor_id')
    mac_address = properties.get('device_address')
    id_vendor_name, icon_url = "N/A", "N/A"

    if vendor_id in VENDOR_ID_MAP:
        id_vendor_name = VENDOR_ID_MAP[vendor_id]["name"]
        icon_url = f"https://cdn.simpleicons.org/{VENDOR_ID_MAP[vendor_id]['slug']}/FFFFFF"
    
    print(f"   - Vendor ID: {vendor_id or 'N/A'} ({id_vendor_name})")
    print(f"   - Icon URL: {icon_url}")

    if not mac_address:
        print("   - MAC Address: N/A")
        return
    
    mac_vendor_name = get_mac_vendor(mac_address)
    print(f"   - MAC Address: {mac_address} ({mac_vendor_name})")

    if id_vendor_name != "N/A" and "failed" not in mac_vendor_name and "not found" not in mac_vendor_name:
        if id_vendor_name.split(',')[0].lower() in mac_vendor_name.lower():
            print("   - ✅ Match: Vendor ID and MAC address vendors are consistent.")
        else:
            print(f"   - ⚠️ Mismatch: ID is '{id_vendor_name}', but MAC is '{mac_vendor_name}'.")
    else:
        print("   - ℹ️ Status: Cannot compare vendors due to missing data.")

# --- Main Application Logic ---
def analyze_bluetooth_data(xml_bytes):
    """Parses data and separates devices into Connected and Not Connected."""
    data = plistlib.loads(xml_bytes)
    items_dict = data[0].get('_items', [{}])[0]
    
    connected_devices_found = False
    not_connected_list = []

    print("\n--- ✅ Connected Devices ---")
    
    # Iterate through all keys to find all possible device patterns
    for key, value in items_dict.items():
        # Pattern 1: A list of "not connected" devices. Save for later.
        if key == 'device_not_connected':
            not_connected_list = value
            continue

        # Pattern 2: A list of "connected" devices. Process now.
        if key == 'device_connected' and isinstance(value, list):
            for device_entry in value:
                for name, properties in device_entry.items():
                    print_device_details(name, properties)
            connected_devices_found = True
            continue

        # Pattern 3 (NEW): The key is the device name itself. Process now.
        # Check if the value is a dictionary containing typical device properties.
        if isinstance(value, dict) and ('device_address' in value or 'vendor_id' in value):
            print_device_details(key, value)
            connected_devices_found = True

    if not connected_devices_found:
        print("No devices are currently connected.")

    # --- Process the saved list of Not Connected Devices ---
    print("\n--- ❌ Not Connected Devices ---")
    if not not_connected_list:
        print("No known (but not connected) devices found.")
    else:
        for device_entry in not_connected_list:
            for name, properties in device_entry.items():
                print_device_details(name, properties)

def main():
    if sys.platform != 'darwin':
        print("Error: This script is designed for macOS.")
        sys.exit(1)
    try:
        command = ['system_profiler', '-xml', 'SPBluetoothDataType']
        result = subprocess.run(command, capture_output=True, check=True, text=False)
        analyze_bluetooth_data(result.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Error executing system_profiler: {e}")

if __name__ == "__main__":
    main()