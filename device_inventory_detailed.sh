#!/bin/bash

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

REPORT_FILE="$HOME/Desktop/Hardware_Report_$(date +%Y%m%d_%H%M%S).txt"

echo "========== HARDWARE INVENTORY ==========" > "$REPORT_FILE"
echo "Generated: $(date)" >> "$REPORT_FILE"
echo >> "$REPORT_FILE"

echo "===== USB DEVICES (ioreg) =====" >> "$REPORT_FILE"

# Gather USB devices info: vendor, product, serial, locationID, device path
ioreg -p IOUSB -w0 -l | awk '
  BEGIN { in_device=0; vendor=""; product=""; serial=""; location=""; path="" }
  /"IOUSBDevice"/ {in_device=1; vendor=""; product=""; serial=""; location=""; path=""}
  in_device && /"USB Vendor Name" *=/ {sub(/.*= *"/, ""); sub(/".*/, ""); vendor=$0}
  in_device && /"USB Product Name" *=/ {sub(/.*= *"/, ""); sub(/".*/, ""); product=$0}
  in_device && /"USB Serial Number" *=/ {sub(/.*= *"/, ""); sub(/".*/, ""); serial=$0}
  in_device && /"locationID" *=/ {location=$NF}
  in_device && /"IORegistryEntryName" *=/ {sub(/.*= *"/, ""); sub(/".*/, ""); path=$0}
  /^}/ && in_device {
    if (vendor != "" || product != "")
      print vendor "\t" product "\t" serial "\t" location "\t" path
    in_device=0
  }
' >> "$REPORT_FILE"

echo >> "$REPORT_FILE"

echo "===== CAMERA DETAILS (system_profiler) =====" >> "$REPORT_FILE"
system_profiler SPCameraDataType >> "$REPORT_FILE"
echo >> "$REPORT_FILE"

echo "===== USB HUBS & PORTS (system_profiler) =====" >> "$REPORT_FILE"
system_profiler SPUSBDataType >> "$REPORT_FILE"
echo >> "$REPORT_FILE"

echo "===== STORAGE DETAILS (diskutil) =====" >> "$REPORT_FILE"

# List all disks and info
diskutil list | grep '^/dev/' | awk '{print $1}' | while read disk; do
  echo "[DISK UTIL INFO FOR $disk]" >> "$REPORT_FILE"
  diskutil info "$disk" >> "$REPORT_FILE"
  echo >> "$REPORT_FILE"
done

echo "===== SUMMARY =====" >> "$REPORT_FILE"

# Summary counts
usb_count=$(ioreg -p IOUSB -w0 -l | grep -c '"IOUSBDevice"')
camera_count=$(system_profiler SPCameraDataType | grep -c "Model ID:")
disk_count=$(diskutil list | grep '^/dev/' | wc -l)

echo "Total USB devices found: $usb_count" >> "$REPORT_FILE"
echo "Total cameras found: $camera_count" >> "$REPORT_FILE"
echo "Total disks found: $disk_count" >> "$REPORT_FILE"

echo >> "$REPORT_FILE"

echo "Report saved to: $REPORT_FILE"
