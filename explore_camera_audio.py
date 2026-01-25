import plistlib
import subprocess
import json

def explore():
    print("Running system_profiler...")
    try:
        output = subprocess.check_output(["system_profiler", "-xml", "SPCameraDataType", "SPAudioDataType"], text=True)
        plist = plistlib.loads(output.encode('utf-8'))
        
        for dtype in plist:
            name = dtype.get('_dataType', 'Unknown')
            print(f"\n--- {name} ---")
            items = dtype.get('_items', [])
            print(f"Found {len(items)} items")
            
            for i, item in enumerate(items):
                print(f"Item {i}:")
                # Print keys and values (truncated if long)
                for k, v in item.items():
                    val_str = str(v)
                    if len(val_str) > 100: val_str = val_str[:100] + "..."
                    print(f"  {k}: {val_str}")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    explore()
