import sys
import json
import csv
import argparse
from dataclasses import dataclass
from typing import List, Optional

# --- Data classes ---

@dataclass
class USBDevice:
    vendor_id: str
    product_id: str
    vendor_name: Optional[str]
    product_name: Optional[str]
    serial: Optional[str]
    speed: Optional[str]

@dataclass
class DiskInfo:
    name: str
    vendor: Optional[str]
    model: Optional[str]
    serial: Optional[str]
    type: Optional[str]       # HDD/SSD/Hybrid
    capacity: Optional[str]   # human-readable string
    free_space: Optional[str] # human-readable string
    encrypted: bool
    encryption_method: Optional[str]
    smart_health: Optional[str]

# --- Stub functions to gather info (replace with real platform-specific code) ---

def get_usb_devices_cross_platform() -> List[USBDevice]:
    # For demo, return dummy devices
    return [
        USBDevice("1234", "5678", "Acme Corp", "USB Flash Drive", "SN123456", "High-Speed"),
        USBDevice("abcd", "ef01", "Generic", "USB Keyboard", None, "Full-Speed"),
    ]

def get_disks_cross_platform() -> List[DiskInfo]:
    # For demo, return dummy disks
    return [
        DiskInfo(
            name="disk0",
            vendor="Seagate",
            model="ST1000LM035",
            serial="S3Z7XXXXX",
            type="HDD",
            capacity="1 TB",
            free_space="450 GB",
            encrypted=True,
            encryption_method="FileVault",
            smart_health="PASSED",
        ),
        DiskInfo(
            name="disk1",
            vendor="Samsung",
            model="860 EVO",
            serial="S3Z8YYYYY",
            type="SSD",
            capacity="500 GB",
            free_space="200 GB",
            encrypted=False,
            encryption_method=None,
            smart_health="PASSED",
        )
    ]

# --- Serialization helpers ---

def serialize_devices_and_disks(usb_devices: List[USBDevice], disks: List[DiskInfo]) -> dict:
    return {
        "usb_devices": [vars(d) for d in usb_devices],
        "disks": [vars(d) for d in disks],
    }

# --- CSV writing ---

def write_csv(usb_devices: List[USBDevice], disks: List[DiskInfo], csv_file: str):
    try:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # USB Devices
            writer.writerow(["USB Devices"])
            writer.writerow(["Vendor ID", "Product ID", "Vendor Name", "Product Name", "Serial", "Speed"])
            for u in usb_devices:
                writer.writerow([
                    u.vendor_id,
                    u.product_id,
                    u.vendor_name or "",
                    u.product_name or "",
                    u.serial or "",
                    u.speed or "",
                ])
            writer.writerow([])  # blank line

            # Disks
            writer.writerow(["Disks"])
            writer.writerow(["Name", "Vendor", "Model", "Serial", "Type", "Capacity", "Free Space", "Encrypted", "Encryption Method", "SMART Health"])
            for d in disks:
                writer.writerow([
                    d.name,
                    d.vendor or "",
                    d.model or "",
                    d.serial or "",
                    d.type or "",
                    d.capacity or "",
                    d.free_space or "",
                    "Yes" if d.encrypted else "No",
                    d.encryption_method or "",
                    d.smart_health or ""
                ])
        print(f"CSV report saved to {csv_file}")
    except Exception as e:
        print(f"Error writing CSV file: {e}", file=sys.stderr)

# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Cross-platform USB and Disk Forensic Info Tool")
    parser.add_argument('--json', type=str, help="Output JSON file path")
    parser.add_argument('--csv', type=str, help="Output CSV file path")
    args = parser.parse_args()

    usb_devices = get_usb_devices_cross_platform()
    disks = get_disks_cross_platform()

    if args.json:
        report = serialize_devices_and_disks(usb_devices, disks)
        try:
            with open(args.json, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=4)
            print(f"JSON report saved to {args.json}")
        except Exception as e:
            print(f"Error writing JSON file: {e}", file=sys.stderr)

    if args.csv:
        write_csv(usb_devices, disks, args.csv)

    if not args.json and not args.csv:
        # Console output
        print("="*40)
        print("USB Devices Found:")
        if not usb_devices:
            print("No USB devices found or error gathering USB info.")
        else:
            for u in usb_devices:
                print(f"Vendor ID: {u.vendor_id}, Product ID: {u.product_id}")
                print(f"Vendor Name: {u.vendor_name}")
                print(f"Product Name: {u.product_name}")
                print(f"Serial: {u.serial}")
                print(f"Speed: {u.speed}")
                print("-"*20)
        print("="*40)
        print("Disks Found:")
        if not disks:
            print("No disks found or error gathering disk info.")
        else:
            for d in disks:
                print(f"Disk: {d.name}")
                print(f"  Vendor: {d.vendor}")
                print(f"  Model: {d.model}")
                print(f"  Serial: {d.serial}")
                print(f"  Type: {d.type}")
                print(f"  Capacity: {d.capacity}")
                print(f"  Free space: {d.free_space}")
                print(f"  Encrypted: {'Yes' if d.encrypted else 'No'}")
                if d.encrypted:
                    print(f"  Encryption Method: {d.encryption_method}")
                print(f"  SMART Health: {d.smart_health}")
                print("-"*40)

if __name__ == '__main__':
    main()
