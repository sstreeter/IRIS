
import sys
import os
sys.path.insert(0, os.getcwd())
from IRIS.helpers import MockAppInstance, Helpers
from IRIS.reports.system_info import system_hardware_info, usb_camera_bluetooth_report

app = MockAppInstance()
helpers = Helpers(use_mock=False)

print("--- Checking USB Report Data ---")
usb_data = usb_camera_bluetooth_report.get_device_data(helpers, app)
found_usb = False
for dev in usb_data['usb']:
    if "Samsung" in dev['name'] or "Flash" in dev['name']:
        print(f"USB MATCH: {dev}")
        found_usb = True
if not found_usb: print("No matching USB device found.")

print("\n--- Checking Storage Report Data ---")
sys_data = system_hardware_info.get_system_data(helpers, app)
found_storage = False
for disk in sys_data['storage']:
    if "Samsung" in disk['name'] or "Flash" in disk['name'] or "TOOLKIT" in disk['name']:
        print(f"STORAGE MATCH: {disk}")
        found_storage = True
if not found_storage: print("No matching Storage device found.")
