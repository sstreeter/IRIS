import subprocess

def run_ioreg():
    try:
        output = subprocess.check_output(["ioreg", "-p", "IOUSB", "-w0", "-l"], text=True)
        print("--- IOREG OUTPUT START ---")
        lines = output.splitlines()
        for i, line in enumerate(lines[:30]):
            print(f"{i}: {repr(line)}")
        print("--- IOREG OUTPUT END ---")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_ioreg()
