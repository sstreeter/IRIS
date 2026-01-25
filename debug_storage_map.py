
import subprocess
import plistlib
import sys

def run_cmd(cmd):
    print(f"Running: {cmd}")
    try:
        out = subprocess.check_output(cmd.split())
        return out
    except Exception as e:
        print(f"Error: {e}")
        return b""

print("--- DEBUGGING STORAGE MAP ---")

raw_list = run_cmd("diskutil list -plist")
if not raw_list:
    print("No output from diskutil list")
    sys.exit(1)

try:
    plist = plistlib.loads(raw_list)
    print(f"Found {len(plist.get('AllDisksAndPartitions', []))} items in AllDisksAndPartitions")
    
    for d in plist.get('AllDisksAndPartitions', []):
        ident = d.get('DeviceIdentifier')
        internal = d.get('Internal')
        print(f"Disk: {ident}, Internal: {internal} (Raw: {d.get('Internal')})")
        
        # Simulating my logic
        is_external = (d.get('Internal', True) == False)
        print(f"  -> Is External Candidate? {is_external}")
        
        if is_external:
            print(f"  -> Fetching INFO for {ident}...")
            # Run info
            info_raw = run_cmd(f"diskutil info -plist {ident}")
            if info_raw:
                info = plistlib.loads(info_raw)
                loc_id = info.get('LocationID')
                vol_name = info.get('VolumeName', '') or info.get('MediaName', '')
                print(f"  -> LocationID: {loc_id} (Type: {type(loc_id)})")
                print(f"  -> VolumeName: {vol_name}")
                if 'Partitions' in d and not vol_name:
                     print("  -> Checking partitions for name...")

except Exception as e:
    print(f"Exception parsing plist: {e}")
