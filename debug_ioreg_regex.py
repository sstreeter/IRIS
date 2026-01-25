import subprocess
import re

def debug_regex():
    try:
        output = subprocess.check_output(["ioreg", "-p", "IOUSB", "-w0", "-l"], text=True)
        lines = output.splitlines()
        print(f"Total lines: {len(lines)}")
        
        regex = r'^([ \t|]*)\+\-o (.+?)  <class'
        count = 0
        for i, line in enumerate(lines):
            m = re.search(regex, line)
            if m:
                print(f"Match at line {i}: '{m.group(0)}'")
                print(f"  Group 1 (Indent): '{m.group(1)}'")
                print(f"  Group 2 (Name):   '{m.group(2)}'")
                count += 1
                if count >= 5: break
        
        if count == 0:
            print("NO MATCHES FOUND!")
            # Print first few lines to see why
            for i, line in enumerate(lines[:10]):
                print(f"Line {i}: {repr(line)}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_regex()
