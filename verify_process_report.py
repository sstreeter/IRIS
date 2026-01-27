from IRIS.reports.process_software.running_processes_report import generate_running_processes_report, classify_process, parse_ps_aux
from IRIS.helpers import MockAppInstance, Helpers
import os
from unittest.mock import MagicMock

def test_process_report_logic():
    print("--- Testing Classification Logic ---")
    
    test_cases = [
        {"command": "/usr/bin/python3 suspicious.py", "expected_sev": "Warning", "expected_cat": "Shell/Interpreter"},
        {"command": "nc -l -p 4444", "expected_sev": "Critical", "expected_cat": "Network Tool"},
        {"command": "/sbin/launchd", "expected_sev": "System", "expected_cat": "System"},
        {"command": "/Applications/Safari.app/Contents/MacOS/Safari", "expected_sev": "Safe", "expected_cat": "User App"},
        {"command": "./unknown_binary", "expected_sev": "Info", "expected_cat": "Unknown"},
        {"command": "sudo rm -rf /", "expected_sev": "High", "expected_cat": "Unknown"} # Should trigger sudo escalation
    ]
    
    for case in test_cases:
        result = classify_process(case)
        sev = result["severity"]
        cat = result["category"]
        
        # Sudo check overrides logic slightly, so handle that
        expected_sev = case["expected_sev"]
        
        if sev == expected_sev:
            print(f"[PASS] {case['command']} -> {sev} ({cat})")
        else:
            print(f"[FAIL] {case['command']} -> Got {sev}, Expected {expected_sev}")

def test_report_generation():
    print("\n--- Testing Report Generation ---")
    app_instance = MockAppInstance()
    helpers = Helpers(use_mock=True)
    
    # Mock ps aux output
    mock_ps = """USER PID %CPU %MEM VSZ RSS TT STAT STARTED TIME COMMAND
root 1 0.0 0.0 0 0 ?? Ss 0:00.00 /sbin/launchd
user 501 0.0 0.0 0 0 ?? S 0:00.00 /Applications/Safari.app/Contents/MacOS/Safari
user 502 0.0 0.0 0 0 ?? S 0:00.00 python3 script.py
user 503 0.0 0.0 0 0 ?? S 0:00.00 nc 10.0.0.1 80
"""
    helpers.run_command = MagicMock(return_value=mock_ps)
    helpers.os_type = "darwin"
    
    generate_running_processes_report(app_instance, helpers, browser_preference="None")
    
    report_path = os.path.join(app_instance.report_output_directory, "Running_Processes_Report.html")
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            content = f.read()
            
        if "Notable Events" in content and "nc 10.0.0.1 80" in content:
            print("[PASS] 'nc' found in Notable Events")
        else:
            print("[FAIL] 'nc' missing from Notable Events")
            
        if "Background System Processes" in content and "launchd" in content:
             print("[PASS] 'launchd' found in System Processes")
        else:
             print("[FAIL] 'launchd' classification failed")
             
    else:
        print("[FAIL] Report not created")

if __name__ == "__main__":
    test_process_report_logic()
    test_report_generation()
