import os
import sys
from IRIS.helpers import MockAppInstance, Helpers

# Add parent directory to sys.path to allow absolute imports
sys.path.append(os.getcwd())

# Import new reports
from IRIS.reports.network.ping_util_report import generate_ping_report
from IRIS.reports.network.whois_report import generate_whois_report
from IRIS.reports.user_security.console_log_report import generate_console_log_report
from IRIS.reports.system_info.images_report import generate_images_report
from IRIS.reports.network.network_config_report import generate_network_config_report

def verify():
    app = MockAppInstance()
    helpers = Helpers()
    
    app.log_output("=== Verifying New Reports ===")
    
    # 1. Images Report (Non-interactive)
    app.log_output("\n[1/5] Verifying Images Report...")
    generate_images_report(app, helpers, browser_preference="None")
    
    # 2. Console Log Report (Requires Sudo, might prompt)
    app.log_output("\n[2/5] Verifying Console Log Report...")
    generate_console_log_report(app, helpers, browser_preference="None")
    
    # 3. Network Config Report (Verify MAC Vendor)
    app.log_output("\n[3/5] Verifying Network Config (MAC Vendor) Report...")
    generate_network_config_report(app, helpers, browser_preference="None")

    # 4. Ping Report (Interactive - skipping in auto-run if possible or using target)
    app.log_output("\n[4/5] Verifying Ping Report (Target: 127.0.0.1)...")
    generate_ping_report(app, helpers, target="127.0.0.1", browser_preference="None")
    
    # 5. WHOIS Report (Target: google.com)
    app.log_output("\n[5/5] Verifying WHOIS Report (Target: google.com)...")
    generate_whois_report(app, helpers, target="google.com", browser_preference="None")

    app.log_output("\n=== Verification Complete ===")
    app.log_output(f"Reports should be in: {os.path.abspath(app.report_output_directory)}")

if __name__ == "__main__":
    verify()
