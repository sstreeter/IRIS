import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import plistlib
import json
from IRIS.reports.system_info.system_hardware_info import generate_system_hardware_report
from IRIS.helpers import MockAppInstance, Helpers
import os
import re

def test_visual_hierarchy():
    app_instance = MockAppInstance()
    helpers = Helpers(use_mock=True)
    
    # Mock system commands
    def mock_run_command(command, **kwargs):
        if "SPHardwareDataType" in command and "-json" not in command:
            return "Hardware Overview:\n Model Name: MockMac\n"

        if "diskutil list -plist" in command:
             # Logic:
             # disk0: Root Physical
             # disk0s2: Partition that is a Physical Store
             # disk1: Synthesized Container, hosted on disk0s2
             # disk2: Another Physical Disk (External)
             plist_data = {
                 "AllDisksAndPartitions": [
                     # disk0
                     {
                         "DeviceIdentifier": "disk0", "VolumeName": "Physical SSD", "Internal": True, "WholeDisk": True,
                         "Partitions": [{"DeviceIdentifier": "disk0s1"}, {"DeviceIdentifier": "disk0s2"}]
                     },
                     # disk1 (Container - should be NESTED under disk0s2 in output)
                     {
                         "DeviceIdentifier": "disk1", "VolumeName": "Synthesized", "Internal": False, "WholeDisk": True,
                         "APFSPhysicalStores": [{"DeviceIdentifier": "disk0s2"}],
                         "Partitions": [{"DeviceIdentifier": "disk1s1", "VolumeName": "Macintosh HD", "Content": "Apple_APFS"}]
                     },
                     # disk2 (External - should be Root)
                     {
                         "DeviceIdentifier": "disk2", "VolumeName": "External SSD", "Internal": False, "WholeDisk": True,
                         "Partitions": [{"DeviceIdentifier": "disk2s1"}]
                     }
                 ]
             }
             return plistlib.dumps(plist_data).decode('utf-8')
             
        if "diskutil list" in command and "-plist" not in command:
             return "/dev/disk0 ... \n/dev/disk1 (synthesized) ... \n/dev/disk2 (external) ..."
        
        if "system_profiler -json" in command:
             return json.dumps([])
        
        return ""

    helpers.run_command = mock_run_command
    
    print("Generating System Report with Visual Hierarchy...")
    generate_system_hardware_report(app_instance, helpers, browser_preference="None")
    
    report_path = os.path.join(app_instance.report_output_directory, "System_Hardware_Report.html")
    if os.path.exists(report_path):
        with open(report_path) as f: content = f.read()
        
        print("\n--- Verification Checks ---")
        
        # 1. disk0 and disk2 should be at top level
        # We can check by checking indentation style or structure?
        
        if "disk0 -" in content:
            print("✅ disk0 present.")
            
        if "disk2 -" in content:
            print("✅ disk2 present.")
            
        # 2. disk1 should be present
        if "disk1 -" in content:
            print("✅ disk1 present.")
            
            # 3. Check nesting using indentation style
            # Look for disk1 header block
            # <details ... style='margin-left: 20px; ...'> ... disk1 ...
            
            # Check if margin-left: 20px exists in the file at all?
            if "margin-left: 20px" in content:
                 print("✅ Indentation style found.")
                 
                 # More robust: Check if disk1 is inside the margin-left: 20px block
                 # We can use regex to find the details tag before disk1
                 match = re.search(r"<details[^>]*style='[^']*margin-left: 20px[^']*'>.*?disk1", content, re.DOTALL)
                 if match:
                     print("✅ disk1 is visually nested.")
                 else:
                     print("❌ disk1 visual nesting failed.")
            else:
                 print("❌ Indentation style missing (Hierarchy failed).")
        else:
             print("❌ disk1 missing from report.")

if __name__ == "__main__":
    test_visual_hierarchy()
