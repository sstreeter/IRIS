
import subprocess
import plistlib
import sys

def run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd.split())
        return out
    except Exception as e:
        print(f"Error {cmd}: {e}")
        return b""

print("--- DEBUG APFS & LOCATION ID ---")

# 1. Dump AllDisks structure to check APFSPhysicalStores linkage
raw_list = run_cmd("diskutil list -plist")
plist = plistlib.loads(raw_list)
all_disks = plist.get('AllDisksAndPartitions', [])
store_map = {}

print(f"Total Disks: {len(all_disks)}")
for d in all_disks:
    did = d.get('DeviceIdentifier')
    if 'APFSPhysicalStores' in d:
        print(f"Synthesized Container Found: {did}")
        for ps in d['APFSPhysicalStores']:
            ps_id = ps.get('DeviceIdentifier')
            print(f"  -> Backed by Physical Store: {ps_id}")
            store_map[ps_id] = d

# 2. Check Specific Disks (disk4, disk6)
targets = ["disk4", "disk6"] 
for t in targets:
    print(f"\nChecking {t}:")
    info_raw = run_cmd(f"diskutil info -plist {t}")
    if not info_raw: 
        print("  (Not found)")
        continue
    
    info = plistlib.loads(info_raw)
    print("  Keys found:", list(info.keys()))
    print(f"  LocationID: {info.get('LocationID')}")
    print(f"  DeviceTreePath: {info.get('DeviceTreePath')}")
    print(f"  IOKitPath: {info.get('IOKitPath')}") # Sometimes called IOKitPath
    print(f"  Serial: {info.get('SolidStateMediaType')}") # Just testing random keys? No.
    # Look for likely serial keys
    for k,v in info.items():
        if 'serial' in k.lower() or 'vendor' in k.lower() or 'product' in k.lower():
             print(f"  {k}: {v}")


