from IRIS.reports.network.network_config_report import generate_network_config_report
from IRIS.helpers import MockAppInstance, Helpers
import os
from unittest.mock import MagicMock

def test_network_report_generation():
    app_instance = MockAppInstance()
    helpers = Helpers(use_mock=True)
    
    # Mock run_command to return networksetup and system_profiler data
    def mock_run_command(command, check_shell=False, app_instance=None):
        if "networksetup -listallhardwareports" in command:
            return """
Hardware Port: Wi-Fi
Device: en0
Ethernet Address: aa:bb:cc:dd:ee:ff

Hardware Port: Ethernet Adapter (en3)
Device: en3
Ethernet Address: 11:22:33:44:55:66
"""
        if "system_profiler -xml SPNetworkDataType" in command:
            # Minimal plist XML with en0 having correct MAC and en3 having N/A
            return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<array>
    <dict>
        <key>_items</key>
        <array>
            <dict>
                <key>_name</key>
                <string>Wi-Fi</string>
                <key>interface</key>
                <string>en0</string>
                <key>hardware_address</key>
                <string>aa:bb:cc:dd:ee:ff</string>
                <key>ip_address</key>
                <array><string>192.168.1.100</string></array>
            </dict>
            <dict>
                <key>_name</key>
                <string>Ethernet Adapter (en3)</string>
                <key>interface</key>
                <string>en3</string>
                <key>hardware_address</key>
                <string>N/A</string>
                <key>ip_address</key>
                <array><string>10.0.0.5</string></array>
            </dict>
        </array>
    </dict>
</array>
</plist>
"""
        return ""

    helpers.run_command = MagicMock(side_effect=mock_run_command)
    helpers.os_type = "darwin" # Force mac parsing path
    
    print("Generating Network Config Report...")
    generate_network_config_report(app_instance, helpers, browser_preference="None")
    
    report_path = os.path.join(app_instance.report_output_directory, "Network_Config_Report.html")
    
    if os.path.exists(report_path):
        print(f"Report generated at {report_path}")
        with open(report_path, "r") as f:
            content = f.read()
            
        print("\n--- Checking for MAC Addresses ---")
        if "aa:bb:cc:dd:ee:ff" in content:
            print("[PASS] Wi-Fi MAC found")
        else:
            print("[FAIL] Wi-Fi MAC missing")
            
        if "11:22:33:44:55:66" in content:
            print("[PASS] En3 MAC found (Fixed from N/A)")
        else:
            print("[FAIL] En3 MAC missing/still N/A")
            
    else:
        print("[FAIL] Report file was not created.")

if __name__ == "__main__":
    test_network_report_generation()
