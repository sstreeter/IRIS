import sys
import os
import json
from typing import Dict, Any

# Mock Helpers
class MockHelpers:
    def __init__(self):
        self.os_type = "darwin"
    def run_command(self, cmd, check_shell=False, app_instance=None):
        if "system_profiler -json SPCameraDataType" in cmd:
            return json.dumps({"SPCameraDataType": [
                {
                    "_name": "C922 Pro Stream Webcam",
                    "spcamera_model-id": "UVC Camera VendorID_1133 ProductID_2140",
                    "spcamera_unique-id": "0x1133100046d085c"
                },
                {
                    "_name": "FaceTime HD Camera",
                    "spcamera_model-id": "FaceTime HD Camera",
                    "spcamera_unique-id": "EBB0ACC7-C7DB-49F1-B1FD-C77F4E234E8C"
                }
            ]})
        if "log show" in cmd:
            return json.dumps([
                {"eventMessage": "PowerOn", "processImagePath": "/usr/libexec/appleh13camerad"}
            ])
        return ""

class MockAppInstance:
    def log_output(self, msg):
        print(f"LOG: {msg}")

# Add path to IRISX
sys.path.append("/Users/spencer/Projects/python/IRISX")

from IRIS.reports.system_info.system_hardware_info import correlate_vid_pid, get_camera_context, render_device_section

print("--- Testing VID/PID Correlation ---")
# Logitech C922 (Decimal IDs from system_profiler)
print(f"C922 Correlation: {correlate_vid_pid('1133', '2140')}")
# Apple FaceTime (Hex-ish IDs)
print(f"Apple Correlation: {correlate_vid_pid('05ac', '8514')}")
# Unknown
print(f"Unknown Correlation: {correlate_vid_pid('1234', '5678')}")

print("\n--- Testing Camera Context ---")
helpers = MockHelpers()
app = MockAppInstance()
ctx = get_camera_context(helpers, app)
print(f"Camera Context: {json.dumps(ctx, indent=2)}")

print("\n--- Testing Render Logic (Partial) ---")
device_dict = {
    "Camera": [
        {
            "_name": "C922 Pro Stream Webcam",
            "spcamera_model-id": "UVC Camera VendorID_1133 ProductID_2140"
        }
    ]
}
extra_context = {"camera": ctx}
html = render_device_section("Hardware", device_dict, extra_context)
if "Verified HW: Logitech C922 Pro Stream Webcam" in html:
    print("SUCCESS: Correlation found in HTML output!")
if "In Use" in html:
    print("SUCCESS: 'In Use' badge found in HTML output!")
if "Max Resolution" in html:
    print("SUCCESS: Tech specs found in HTML output!")

# Check for the nesting fix by seeing if Camera is rendered correctly when Audio is also present
device_dict_full = {
    "Audio": [{"_name": "Built-in Output"}],
    "Camera": [{"_name": "C922 Pro Stream Webcam", "spcamera_model-id": "UVC Camera VendorID_1133 ProductID_2140"}]
}
extra_context_full = {"audio": {"volume": {}, "active_processes": {}}, "camera": ctx}
html_full = render_device_section("Hardware", device_dict_full, extra_context_full)
if "Verified HW: Logitech C922 Pro Stream Webcam" in html_full:
    print("SUCCESS: Nested Camera logic fixed!")
else:
    print("FAILURE: Camera logic still failing when Audio is present.")
