import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import sys
import os

# Ensure IRIS package is discoverable
sys.path.insert(0, os.getcwd())

from IRIS.helpers import MockAppInstance, Helpers
from IRIS.reports.system_info import system_hardware_info, usb_camera_bluetooth_report

def test_system_report():
    print("--- Testing System Hardware Report ---")
    app = MockAppInstance()
    helpers = Helpers(use_mock=False) # Use Live for real diskutil check if possible, or True if purely relying on mocks
    
    print(f"Detected OS Type: {helpers.os_type}")
    
    # 1. System Data
    data = system_hardware_info.get_system_data(helpers, app)
    print("\n[SYSTEM DATA RESULT]")
    # Print storage specifically to check recursion
    print(f"Storage Items Found: {len(data['storage'])}")
    for disk in data['storage']:
        print(f" - {disk['name']}: {disk['mount_point']} ({disk['used']} used)")

def test_usb_report():
    print("\n--- Testing USB Report ---")
    app = MockAppInstance()
    helpers = Helpers(use_mock=False) # Use Live

    # 1. USB Data
    data = usb_camera_bluetooth_report.get_device_data(helpers, app)
    print("\n[USB DATA RESULT]")
    
    print("Graph Roots:")
    for root in data['usb_tree']:
        print(f" - {root.get('chart_label', root.get('name'))}")
    
    if 'displays' in data:
        print(f"Displays Found: {len(data['displays'])}")
        for d in data['displays']:
            print(f" - {d['name']} ({d['resolution']}) via {d['connection_type']}")
            
    print(f"USB Devices: {len(data['usb'])}")
    for d in data['usb']:
        print(f" - {d['name']} ({d['vendor_id']}:{d['product_id']})")

    print(f"Camera Devices: {len(data['camera'])}")
    for d in data['camera']:
        print(f" - {d['name']} [Manuf: {d.get('manufacturer')}, Serial: {d.get('serial')}]")
        if 'details' in d:
            print(f"   Details: {d['details']}")

    if 'audio' in data:
        print(f"Audio Devices: {len(data['audio'])}")
        for d in data['audio']:
            print(f" - {d['name']}")

    print(f"Bluetooth Devices: {len(data['bluetooth'])}")
    for d in data['bluetooth']:
        print(f" - {d['name']}")

def test_logon_report():
    print("\n--- Testing Logon Report ---")
    app = MockAppInstance()
    helpers = Helpers(use_mock=False)
    
    from IRIS.reports.user_security import logon_report
    data = logon_report.get_logon_data(helpers, app)
    print(f"Logon Events Found: {data['summary']['total']}")
    # Print first few
    for l in data['logons'][:3]:
        print(f" - {l['raw']}")

def test_network_report():
    print("\n--- Testing Network Report ---")
    app = MockAppInstance()
    helpers = Helpers(use_mock=False)
    
    from IRIS.reports.network import tcp_connections_report
    conns = tcp_connections_report.get_active_connections(helpers, app)
    print(f"Connections Found: {len(conns)}")
    # Print first few LISTENers
    print("Listening Ports (Top 5):")
    listeners = [c for c in conns if "LISTEN" in c['state']]
    for c in listeners[:5]:
        print(f" - [{c['protocol']}] {c['local']} (PID: {c['pid']} / {c['process']})")

    # Print first few ESTABLISHED
    # Print first few ESTABLISHED
    print("Established Connections (Top 5):")
    established = [c for c in conns if "ESTABLISHED" in c['state']]
    for c in established[:5]:
        print(f" - [{c['protocol']}] {c['local']} -> {c['remote']} (PID: {c['pid']} / {c['process']})")

def test_network_config():
    print("\n--- Testing Network Config Report ---")
    app = MockAppInstance()
    helpers = Helpers(use_mock=False)
    
    from IRIS.reports.network import network_config_report
    ifaces = network_config_report.get_interface_config(helpers, app)
    print(f"Interfaces Found: {len(ifaces)}")
    for i in ifaces:
        print(f" - {i['name']} ({i['device']}) MAC: {i['mac_address']}")
        if i['ipv4']: print(f"   IPv4: {i['ipv4']}")
        if i['ipv6']: print(f"   IPv6: {i['ipv6']}")

if __name__ == "__main__":
    test_system_report()
    test_usb_report()
    test_logon_report()
    test_network_report()
    test_network_config()
