import sys
import plistlib
from typing import List, Dict, Any
from ...helpers import MockAppInstance, Helpers

def _find_devices_with_key(items: List[Dict], key: str, results: List[Dict]):
    for item in items:
        if key in item and item.get(key):
            results.append(item)
        if '_items' in item and isinstance(item.get('_items'), list):
            _find_devices_with_key(item['_items'], key, results)

def _parse_system_profiler_xml(xml_data: str, app_instance: Any) -> List[Dict]:
    if not xml_data:
        return []
    try:
        data = plistlib.loads(xml_data.encode('utf-8'), fmt=plistlib.FMT_XML)
        return data[0].get('_items', []) if data else []
    except Exception as e:
        app_instance.log_output(f"Error parsing system_profiler XML: {e}")
        return []

def _vendor_svg(vendor_id: str) -> str:
    vendor_svgs = {
        "0x004C": '<svg width="16" height="16"><circle cx="8" cy="8" r="7" fill="gray"/><text x="8" y="12" font-size="8" fill="white" text-anchor="middle"></text></svg>',
        "0x046D": '<svg width="16" height="16"><rect width="16" height="16" fill="#0073CF"/><text x="8" y="12" font-size="7" fill="white" text-anchor="middle">Logi</text></svg>',
        "0x0006": '<svg width="16" height="16"><rect width="16" height="16" fill="#737373"/><text x="8" y="12" font-size="7" fill="white" text-anchor="middle">MS</text></svg>',
    }
    return vendor_svgs.get(vendor_id, '')

def _sortable_table_script() -> str:
    return """
<script>
document.querySelectorAll("table").forEach(table => {
  const headers = table.querySelectorAll("th");
  headers.forEach((th, colIndex) => {
    th.style.cursor = "pointer";
    th.onclick = () => {
      const rows = Array.from(table.querySelectorAll("tr:nth-child(n+2)"));
      const sorted = rows.sort((a, b) =>
        a.cells[colIndex].innerText.localeCompare(b.cells[colIndex].innerText)
      );
      rows.forEach(row => table.appendChild(row));
    };
  });
});
</script>
"""

def generate_usb_camera_bluetooth_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    app_instance.log_output("\n--- Generating USB, Camera & Bluetooth Devices Report ---")

    html_body = "<h2>Connected Peripheral Devices</h2>"

    if sys.platform != "darwin":
        html_body += "<p>This report only supports macOS.</p>"
    else:
        # --- USB Devices ---
        html_body += "<h3>USB Devices</h3>"
        usb_xml = helpers.run_command("system_profiler -xml SPUSBDataType", check_shell=True, app_instance=app_instance)
        usb_items = _parse_system_profiler_xml(usb_xml, app_instance)
        usb_devs = []
        _find_devices_with_key(usb_items, 'vendor_id', usb_devs)

        if usb_devs:
            html_body += "<table><tr><th>Name</th><th>Manufacturer</th><th>Vendor ID</th><th>Product ID</th><th>Serial #</th></tr>"
            for dev in usb_devs:
                html_body += f"<tr><td>{dev.get('_name','N/A')}</td><td>{dev.get('manufacturer','N/A')}</td>"
                html_body += f"<td>{dev.get('vendor_id','')}</td><td>{dev.get('product_id','')}</td><td>{dev.get('serial_num','')}</td></tr>"
            html_body += "</table>"
        else:
            html_body += "<p>No USB devices found.</p>"

        # --- Camera Devices ---
        html_body += "<h3>Camera Devices</h3>"
        cam_xml = helpers.run_command("system_profiler -xml SPCameraDataType", check_shell=True, app_instance=app_instance)
        cam_items = _parse_system_profiler_xml(cam_xml, app_instance)
        if cam_items:
            html_body += "<table><tr><th>Name</th><th>Model ID (Vendor/Product)</th></tr>"
            for cam in cam_items:
                html_body += f"<tr><td>{cam.get('_name','')}</td><td>{cam.get('model_id','')}</td></tr>"
            html_body += "</table>"
        else:
            html_body += "<p>No camera devices found.</p>"

        # --- Bluetooth Devices ---
        html_body += "<h3>Bluetooth Devices</h3>"
        bt_xml = helpers.run_command("system_profiler -xml SPBluetoothDataType", check_shell=True, app_instance=app_instance)
        bt_tree = _parse_system_profiler_xml(bt_xml, app_instance)
        bt_devs = []
        _find_devices_with_key(bt_tree, 'device_address', bt_devs)

        if bt_devs:
            html_body += "<table><tr><th>Name</th><th>Vendor</th><th>Product</th><th>Device Address</th><th>Icon</th></tr>"
            for dev in bt_devs:
                html_body += "<tr>"
                html_body += f"<td>{dev.get('_name','')}</td>"
                html_body += f"<td>{dev.get('vendor_id','')}</td>"
                html_body += f"<td>{dev.get('product_id','')}</td>"
                html_body += f"<td>{dev.get('device_address','')}</td>"
                html_body += f"<td>{_vendor_svg(dev.get('vendor_id',''))}</td>"
                html_body += "</tr>"
            html_body += "</table>"
        else:
            html_body += "<p>No Bluetooth devices found.</p>"

    html_body += _sortable_table_script()

    helpers.generate_report_html(
        app_instance,
        app_instance.suspect_computer_name,
        "USB_Camera_Bluetooth_Report.html",
        "USB, Camera & Bluetooth Devices Report",
        html_body,
        browser_preference=browser_preference
    )
