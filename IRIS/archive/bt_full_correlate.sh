#!/bin/bash

# Helper: convert ioreg hex MAC to colon format
hex_to_mac() {
  echo "$1" | sed 's/^.//;s/.$//' | \
  sed 's/\(..\)/\1:/g;s/:$//' | tr '[:upper:]' '[:lower:]'
}

echo "=== SYSTEM PROFILER: Bluetooth Controller ==="
sp_info=$(system_profiler SPBluetoothDataType)

sp_mac=$(echo "$sp_info" | grep -i "Address:" | head -1 | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
sp_fw=$(echo "$sp_info" | grep -i "Firmware Version:" | head -1 | awk -F': ' '{print $2}')
sp_transport=$(echo "$sp_info" | grep -i "^ *Transport:" | head -1 | awk -F': ' '{print $2}')
sp_vendor=$(echo "$sp_info" | grep -i "Manufacturer:" | head -1 | awk -F'[(]' '{print $2}' | tr -d ')')
sp_lmp=$(echo "$sp_info" | grep -i "LMP Version:" | head -1 | awk -F'[()]' '{print $2}')

echo "Controller MAC Address: $sp_mac"
echo "Firmware Version: $sp_fw"
echo "Transport: $sp_transport"
echo "Manufacturer: $sp_vendor"
echo "LMP Version: $sp_lmp"
echo ""

echo "=== IOREG: Bluetooth Controller Info ==="
ioreg_output=$(ioreg -r -c IOBluetoothHostController)

# Extract BD_ADDR hex string (should be 12 hex chars)
ioreg_mac_hex=$(echo "$ioreg_output" | grep -m1 '"BD_ADDR" =' | awk -F'= ' '{print $2}' | tr -d ' <>' | tr -d '\n' | tr -d '\r')
ioreg_mac_fmt=$(hex_to_mac "$ioreg_mac_hex")

# Extract firmware version, transport
ioreg_fw=$(echo "$ioreg_output" | grep -m1 '"FirmwareVersion"' | awk -F'= ' '{print $2}' | tr -d '"')
ioreg_transport=$(echo "$ioreg_output" | grep -m1 '"Transport"' | awk -F'= ' '{print $2}' | tr -d '"')

# Extract vendor and product IDs (handle dictionary format)
vendor_raw=$(echo "$ioreg_output" | grep -m1 '"ProductID"')
ioreg_vendor=$(echo "$vendor_raw" | sed -n 's/.*ManufacturerID=\([0-9]*\).*/\1/p')
ioreg_product=$(echo "$vendor_raw" | sed -n 's/.*ProductID=\([0-9]*\).*/\1/p')

ioreg_lmp=$(echo "$ioreg_output" | grep -m1 '"LMPVersion"' | awk -F'= ' '{print $2}')

echo "Controller MAC Address: $ioreg_mac_fmt"
echo "Firmware Version: $ioreg_fw"
echo "Transport: $ioreg_transport"
echo "Vendor ID: $ioreg_vendor"
echo "Product ID: $ioreg_product"
echo "LMP Version: $ioreg_lmp"
echo ""

if [[ "$sp_mac" == "$ioreg_mac_fmt" ]]; then
  echo "✅ Controller MAC addresses match!"
else
  echo "⚠️ Controller MAC addresses do NOT match!"
fi

echo ""
echo "=== SYSTEM PROFILER: Paired Bluetooth Devices ==="

# Extract paired devices (Name + MAC) from system_profiler output
echo "$sp_info" | awk '
  BEGIN { RS = ""; FS = "\n" }
  /Address:/ && /Name:/ {
    mac=""; name="";
    for(i=1; i<=NF; i++) {
      if ($i ~ /Address:/) {
        split($i,a,": ");
        mac=tolower(a[2]);
      }
      if ($i ~ /Name:/) {
        split($i,a,": ");
        name=a[2];
      }
    }
    if(mac != "" && name != "") {
      print mac "|" name;
    }
  }
' > /tmp/bt_paired_devices.txt

# Dump all IOBluetoothDevice entries from ioreg for matching MACs
ioreg -r -c IOBluetoothDevice > /tmp/ioreg_devices.txt

echo "Paired Devices (MAC | Name | ioreg Match Found):"
while IFS="|" read -r mac name; do
  # Normalize MAC for grep: remove colons and uppercase
  mac_no_colon=$(echo "$mac" | sed 's/://g' | tr '[:lower:]' '[:upper:]')
  found=$(grep -i "$mac_no_colon" /tmp/ioreg_devices.txt)

  if [[ -n "$found" ]]; then
    echo "$mac | $name | Yes"
  else
    echo "$mac | $name | No"
  fi
done < /tmp/bt_paired_devices.txt

# Clean up
rm /tmp/bt_paired_devices.txt /tmp/ioreg_devices.txt
