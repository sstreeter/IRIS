import sys
import os

# Fix path to allow importing IRIS
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from IRIS.reports.process_software.installed_software_report import generate_installed_software_report
from IRIS.helpers import Helpers

class MockApp:
    def __init__(self):
        self.suspect_computer_name = "Test-Mac"
        self.report_output_directory = os.getcwd()
    
    def log_output(self, msg):
        print(msg)

app = MockApp()
helpers = Helpers(use_mock=False)

print("Generating Installed Software Report...")
generate_installed_software_report(app, helpers, browser_preference="None")

report_path = "Installed_Software_Report.html"
if os.path.exists(report_path):
    print(f"Successfully generated report: {report_path}")
    # Quick check for content
    with open(report_path, "r") as f:
        content = f.read()
        if "window.appData" in content and "system_profiler" in content: # Wait, system_profiler command isn't in content, but json_payload is
             pass
        if "<table class=\"app-table\">" in content:
            print("[PASS] Table structure found")
        if "window.appData" in content:
            print("[PASS] JSON data payload found")
else:
    print("[FAIL] Report file not found")
