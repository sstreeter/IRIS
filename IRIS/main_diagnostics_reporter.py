import os
import sys

# --- IMPORTANT: How to Run This Script ---
# This script is designed to be run as a Python module from the directory
# *containing* the 'IRIS' package. For your setup, this means:
#
# 1. Navigate to: /Users/spencer/Documents/Python/IRISX/
#    (i.e., the parent directory of your 'IRIS' folder)
#    cd /Users/spencer/Documents/Python/IRISX/
#
# 2. Run the script using the -m flag:
#    /usr/local/bin/python3 -m IRIS.main_diagnostics_reporter
#
# This method correctly sets up Python's module search path for packages
# and enables imports to work.
# Do NOT run this script directly from within the IRIS directory using its filename.

# --- DEBUGGING: Print sys.path and current module name ---
print(f"--- Debug Info (from {__file__}) ---")
print(f"__name__: {__name__}")
print(f"sys.path: {sys.path}")
print("------------------------------------")
# --- END DEBUGGING ---

# Import necessary components using absolute imports from the IRIS package.
# This explicitly references the modules within the 'IRIS' package.
from IRIS.helpers import MockAppInstance, Helpers

# Group 1: Core System & Hardware
from IRIS.reports.system_info.system_hardware_info import generate_system_hardware_report
from IRIS.reports.system_info.usb_camera_bluetooth_report import generate_usb_camera_bluetooth_report

# Group 2: User & Security
from IRIS.reports.user_security.local_accounts_report import generate_local_accounts_report
from IRIS.reports.user_security.logon_report import generate_logon_report
from IRIS.reports.user_security.antivirus_status_report import generate_antivirus_status_report
from IRIS.reports.user_security.web_history_report import generate_web_history_report

# Group 3: Network & Connectivity
from IRIS.reports.network.tcp_connections_report import generate_tcp_connections_report
from IRIS.reports.network.network_config_report import generate_network_config_report
from IRIS.reports.network.firewall_rules_report import generate_firewall_rules_report

# Group 4: Running State & Software
from IRIS.reports.process_software.running_processes_report import generate_running_processes_report
from IRIS.reports.process_software.installed_software_report import generate_installed_software_report

# Group 5: Persistence & Malicious Activity
from IRIS.reports.persistence_malware.scheduled_tasks_report import generate_scheduled_tasks_report
from IRIS.reports.persistence_malware.startup_items_report import generate_startup_items_report
from IRIS.reports.persistence_malware.script_check_report import generate_script_check_report
from IRIS.reports.persistence_malware.process_persistence_report import generate_process_persistence_report


def run_all_diagnostics():
    """Initializes the application and runs all diagnostic reports."""
    app_instance = MockAppInstance()
    helpers = Helpers()

    app_instance.log_output("--- Starting Comprehensive Diagnostics Report ---")

    # Group 1: Core System & Hardware
    generate_system_hardware_report(app_instance, helpers)
    generate_usb_camera_bluetooth_report(app_instance, helpers)

    # Group 2: User & Security
    generate_local_accounts_report(app_instance, helpers)
    generate_logon_report(app_instance, helpers)
    generate_antivirus_status_report(app_instance, helpers)
    generate_web_history_report(app_instance, helpers)

    # Group 3: Network & Connectivity
    generate_tcp_connections_report(app_instance, helpers)
    generate_network_config_report(app_instance, helpers)
    generate_firewall_rules_report(app_instance, helpers)

    # Group 4: Running State & Software
    generate_running_processes_report(app_instance, helpers)
    generate_installed_software_report(app_instance, helpers)

    # Group 5: Persistence & Malicious Activity
    generate_scheduled_tasks_report(app_instance, helpers)
    generate_startup_items_report(app_instance, helpers)
    generate_script_check_report(app_instance, helpers)
    generate_process_persistence_report(app_instance, helpers)

    app_instance.log_output("\n--- All Diagnostic Reports Completed ---")
    app_instance.log_output(f"Reports saved to: {os.path.abspath(app_instance.report_output_directory)}")

if __name__ == "__main__":
    run_all_diagnostics()

