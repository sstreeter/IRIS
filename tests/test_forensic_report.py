import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from IRIS.reports.user_security.console_log_report import generate_console_log_report
from IRIS.helpers import Helpers, MockAppInstance

class App:
    def log_output(self, msg):
        print(msg)
    def __getattr__(self, name):
        if name == 'suspect_computer_name':
            return 'Test-Mac'
        return None

helpers = Helpers(use_mock=False)
app = App()

print("Testing Forensic Console Report Generation...")
generate_console_log_report(app, helpers, browser_preference="None")
print("\nTest completed. Check for Diagnostic_Reports in the current directory (or where helpers generate them).")
