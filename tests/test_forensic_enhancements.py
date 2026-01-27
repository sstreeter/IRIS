import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from IRIS.reports.network.network_config_report import generate_network_config_report
from IRIS.reports.user_security.user_activity_report import generate_user_activity_report
from IRIS.reports.system_info.images_report import generate_images_report
from IRIS.helpers import Helpers, MockAppInstance

class App:
    def log_output(self, msg):
        print(msg)
    def __getattr__(self, name):
        if name == 'suspect_computer_name':
            return 'Test-Mac'
        if name == 'report_output_directory':
             import os
             return os.getcwd() # write to current dir
        return None

helpers = Helpers(use_mock=False)
app = App()

# --- TIME RANGE TEST CONFIG ---
# Simulate "Last 24 Hours"
from datetime import datetime, timedelta
now = datetime.now()
app.time_range = {
    "start": now - timedelta(hours=24),
    "end": now
}
print(f"--- TEST CONFIG: Time Range set to Last 24h ({app.time_range['start']} to {app.time_range['end']}) ---")

print("\n--- Testing Network Config Report (MAC Vendor) ---")
generate_network_config_report(app, helpers, browser_preference="None")

print("\n--- Testing User Activity Report (Downloads & Extensions) ---")
generate_user_activity_report(app, helpers, browser_preference="None")

print("\n--- Testing Filesystem Artifacts Report (Disk Images & Visual Media) ---")
generate_images_report(app, helpers, browser_preference="None")

from IRIS.reports.user_security.console_log_report import generate_console_log_report
print("\n--- Testing Console Log Report (Forensic Time Range) ---")
generate_console_log_report(app, helpers, browser_preference="None")
