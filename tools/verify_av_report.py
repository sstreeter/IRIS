import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from IRIS.reports.user_security.antivirus_status_report import generate_antivirus_status_report
from IRIS.helpers import MockAppInstance, Helpers
import os
from unittest.mock import MagicMock

def test_av_report_generation():
    app_instance = MockAppInstance()
    helpers = Helpers(use_mock=True)
    
    # Mock run_command to return specific output for mdatp and XProtect checks
    def mock_run_command(command, check_shell=False, app_instance=None):
        if "mdatp health --field app_version" in command:
            return "101.90.00"
        if "mdatp health --field real_time_protection_enabled" in command:
            return "true"
        if "mdatp health --field definitions_updated" in command:
            return "Jan 23, 2026"
        if "ls /Library/Apple/System/Library/AssetsV2/" in command:
            return "com_apple_MobileAsset_XProtect\nOtherAsset"
        if "defaults read" in command:
            return "1"
        if "ps aux" in command:
             return "user 123 0.0 0.0 0 0 ?? S 0:00.00 /Applications/CrowdStrike/Falcon.app/Contents/MacOS/Falcon"
        return ""

    helpers.run_command = MagicMock(side_effect=mock_run_command)
    
    print("Generating AV Status Report...")
    generate_antivirus_status_report(app_instance, helpers, browser_preference="None")
    
    report_path = os.path.join(app_instance.report_output_directory, "Antivirus_Status_Report.html")
    
    if os.path.exists(report_path):
        print(f"Report generated at {report_path}")
        with open(report_path, "r") as f:
            content = f.read()
            
        print("\n--- Checking for AV Detections ---")
        if "Microsoft Defender" in content:
            print("[PASS] Detected Microsoft Defender")
        else:
            print("[FAIL] Did NOT detect Microsoft Defender")

        if "XProtect (macOS Native)" in content:
            print("[PASS] Detected XProtect")
        else:
            print("[FAIL] Did NOT detect XProtect")
            
        if "Falcon" in content:
             print("[PASS] Detected CrowdStrike Falcon (Fallback)")
        
        print("\n--- Report Content Snippet ---")
        start = content.find("<table")
        end = content.find("</table>")
        if start != -1 and end != -1:
            snippet = content[start:end+8]
            print(snippet)
            if "Severity" in snippet and "Remediation" in snippet:
                print("\n[PASS] Severity and Remediation columns found.")
            else:
                print("\n[FAIL] Severity/Remediation columns missing.")
        else:
            print("Table not found in report.")
            
    else:
        print("[FAIL] Report file was not created.")

if __name__ == "__main__":
    test_av_report_generation()
