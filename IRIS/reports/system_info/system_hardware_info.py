import platform
import sys
import re
import plistlib
from typing import List, Optional, Dict, Any, Union

# Import necessary components from helpers.py using relative path
from ...helpers import MockAppInstance, Helpers, DiskInfo

def generate_system_hardware_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """Gathers and reports general system, hardware, memory, and storage information."""
    app_instance.log_output("\n--- Generating System & Hardware Report ---")
    
    html_body = ""

    # --- General System Information ---
    html_body += "<h2>General System Information</h2><table><tr><th>Attribute</th><th>Value</th></tr>"
    html_body += f"<tr><td>System</td><td>{platform.system()}</td></tr>"
    html_body += f"<tr><td>Node Name</td><td>{platform.node()}</td></tr>"
    html_body += f"<tr><td>Machine Architecture</td><td>{platform.machine()}</td></tr>"
    html_body += f"<tr><td>Processor (Generic)</td><td>{platform.processor()}</td></tr>"
    
    if sys.platform == "win32":
        app_instance.log_output("Gathering detailed Windows system information...")
        output_os = helpers.run_command('systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Manufacturer" /C:"System Model" /C:"Processor(s)" /C:"Total Physical Memory"', app_instance=app_instance)
        if output_os:
            for line in output_os.strip().split('\n'):
                if ":" in line:
                    attr, val = line.split(":", 1)
                    html_body += f"<tr><td>{attr.strip()}</td><td>{val.strip()}</td></tr>"
    
    elif sys.platform == "darwin":
        app_instance.log_output("Gathering detailed macOS system information using `system_profiler`...")

        try:
            sw_info = helpers.run_command("system_profiler SPSoftwareDataType", check_shell=True, app_instance=app_instance)
            if sw_info:
                os_match = re.search(r'System Version: (.+)', sw_info)
                build_match = re.search(r'Build Version: (.+)', sw_info)
                if os_match: html_body += f"<tr><td>macOS Version</td><td>{os_match.group(1).strip()}</td></tr>"
                if build_match: html_body += f"<tr><td>macOS Build</td><td>{build_match.group(1).strip()}</td></tr>"
            
            hw_info = helpers.run_command("system_profiler SPHardwareDataType", check_shell=True, app_instance=app_instance)
            if hw_info:
                processor_match = re.search(r'Processor Name: (.+)', hw_info)
                speed_match = re.search(r'Processor Speed: (.+)', hw_info)
                cores_match = re.search(r'Total Number of Cores: (.+)', hw_info)
                if processor_match: html_body += f"<tr><td>Processor (Detailed)</td><td>{processor_match.group(1).strip()}</td></tr>"
                if speed_match: html_body += f"<tr><td>Processor Speed</td><td>{speed_match.group(1).strip()}</td></tr>"
                if cores_match: html_body += f"<tr><td>Number of Cores</td><td>{cores_match.group(1).strip()}</td></tr>"
        except Exception as e:
            app_instance.log_output(f"Error gathering macOS OS/CPU details: {e}")
            html_body += f"<tr><td colspan='2'>Error gathering detailed macOS OS/CPU info.</td></tr>"

    html_body += """</table>"""

    # --- Memory Information ---
    html_body += "<h2>Memory (RAM) Information</h2><table><tr><th>Metric</th><th>Value</th></tr>"
    if sys.platform == "darwin":
        try:
            total_mem_kb_str = helpers.run_command("sysctl -n hw.memsize", check_shell=True, app_instance=app_instance)
            if total_mem_kb_str:
                total_mem_gb = round(int(total_mem_kb_str.strip()) / (1024**3), 2)
                html_body += f"<tr><td>Total Physical Memory</td><td>{total_mem_gb} GB</td></tr>"
            else:
                app_instance.log_output("Could not retrieve total physical memory via sysctl.")

            vm_stat_output = helpers.run_command("vm_stat", check_shell=True, app_instance=app_instance)
            if vm_stat_output:
                page_size_match = re.search(r'page size of (\d+) bytes', vm_stat_output, re.IGNORECASE)
                page_size_bytes = 4096
                if page_size_match:
                    try:
                        page_size_bytes = int(page_size_match.group(1))
                    except ValueError:
                        app_instance.log_output(f"Warning: Could not parse vm_stat page size value, defaulting to 4KB. Raw match: {page_size_match.group(1)}")
                else:
                    app_instance.log_output("Warning: 'Page size of N bytes' not found in vm_stat output, defaulting to 4KB.")

                page_size_gb = page_size_bytes / (1024**3)

                vm_stats_dict = {}
                for line in vm_stat_output.splitlines():
                    match = re.match(r'\s*Pages\s+(.+?):\s+(\d+)', line)
                    if match:
                        key = match.group(1).strip().replace(' ', '_').lower()
                        value = int(match.group(2))
                        vm_stats_dict[key] = value

                active_gb = round(vm_stats_dict.get('active', 0) * page_size_gb, 2)
                inactive_gb = round(vm_stats_dict.get('inactive', 0) * page_size_gb, 2)
                wired_gb = round(vm_stats_dict.get('wired_down', 0) * page_size_gb, 2)
                compressed_gb = round(vm_stats_dict.get('occupied_by_physical_pages_that_have_been_decompressed', 0) * page_size_gb, 2)
                speculative_gb = round(vm_stats_dict.get('speculative', 0) * page_size_gb, 2)
                throttled_gb = round(vm_stats_dict.get('throttled', 0) * page_size_gb, 2)

                html_body += f"<tr><td>Memory Active</td><td>{active_gb} GB</td></tr>"
                html_body += f"<tr><td>Memory Inactive</td><td>{inactive_gb} GB</td></tr>"
                html_body += f"<tr><td>Memory Wired</td><td>{wired_gb} GB</td></tr>"
                html_body += f"<tr><td>Memory Compressed</td><td>{compressed_gb} GB</td></tr>"
                if speculative_gb > 0:
                    html_body += f"<tr><td>Memory Speculative</td><td>{speculative_gb} GB</td></tr>"
                if throttled_gb > 0:
                    html_body += f"<tr><td>Memory Throttled</td><td>{throttled_gb} GB</td></tr>"
                
                if 'total_mem_gb' in locals():
                    used_approx = active_gb + inactive_gb + wired_gb + compressed_gb + speculative_gb + throttled_gb
                    available_approx = total_mem_gb - used_approx
                    html_body += f"<tr><td>Memory Used (Approx)</td><td>{round(used_approx, 2)} GB</td></tr>"
                    html_body += f"<tr><td>Memory Available (Approx)</td><td>{round(available_approx, 2)} GB</td></tr>"
                else:
                    html_body += f"<tr><td colspan='2'>Memory Used/Available approximation not possible without Total Memory.</td></tr>"

            swap_info_raw = helpers.run_command("sysctl vm.swapusage", check_shell=True, app_instance=app_instance)
            if swap_info_raw:
                pattern = r"total = ([\d.]+[MG]?)\s+used = ([\d.]+[MG]?)\s+free = ([\d.]+[MG]?)"
                match = re.search(pattern, swap_info_raw)

                if match:
                    total_swap, used_swap, free_swap = match.groups()
                    html_body += f"<tr><td>Swap Total</td><td>{total_swap}</td></tr>"
                    html_body += f"<tr><td>Swap Used</td><td>{used_swap}</td></tr>"
                    html_body += f"<tr><td>Swap Free</td><td>{free_swap}</td></tr>"
                else:
                    app_instance.log_output("Could not parse swapusage output with new regex. Raw output: " + swap_info_raw.strip())
                    html_body += "<tr><td colspan='2'>Could not parse swapusage output.</td></tr>"
            else:
                app_instance.log_output("Could not retrieve swapusage info.")

        except Exception as e:
            app_instance.log_output(f"Error gathering macOS Memory details: {e}")
            html_body += f"<tr><td colspan='2'>Error gathering detailed macOS Memory info.</td></tr>"
    elif sys.platform == "win32":
        try:
            wmic_mem_output = helpers.run_command("wmic ComputerSystem get TotalPhysicalMemory", app_instance=app_instance)
            if wmic_mem_output:
                total_mem_bytes = int(wmic_mem_output.split('\n')[1].strip())
                total_mem_gb = round(total_mem_bytes / (1024**3), 2)
                html_body += f"<tr><td>Total Physical Memory</td><td>{total_mem_gb} GB</td></tr>"

            wmic_os_mem_output = helpers.run_command("wmic OS get FreePhysicalMemory,TotalVisibleMemorySize,FreeVirtualMemory,TotalVirtualMemorySize", app_instance=app_instance)
            if wmic_os_mem_output:
                lines = wmic_os_mem_output.strip().split('\n')
                if len(lines) > 1:
                    headers = [h.strip() for h in lines[0].split()]
                    values = [v.strip() for v in lines[1].split()]
                    mem_dict = dict(zip(headers, values))
                    
                    html_body += f"<tr><td>Free Physical Memory</td><td>{round(int(mem_dict.get('FreePhysicalMemory', 0)) / 1024, 2)} MB</td></tr>"
                    html_body += f"<tr><td>Total Visible Memory</td><td>{round(int(mem_dict.get('TotalVisibleMemorySize', 0)) / 1024, 2)} MB</td></tr>"
                    html_body += f"<tr><td>Free Virtual Memory</td><td>{round(int(mem_dict.get('FreeVirtualMemory', 0)) / 1024, 2)} MB</td></tr>"
                    html_body += f"<tr><td>Total Virtual Memory</td><td>{round(int(mem_dict.get('TotalVirtualMemorySize', 0)) / 1024, 2)} MB</td></tr>"
        except Exception as e:
            app_instance.log_output(f"Error gathering Windows Memory details: {e}")
            html_body += f"<tr><td colspan='2'>Error gathering detailed Windows Memory info.</td></tr>"
    html_body += """</table>"""

    # --- Storage Information ---
    html_body += "<h2>Storage Information</h2><table><tr><th>Drive/Volume</th><th>Size</th><th>Used</th><th>Available</th><th>Filesystem</th><th>Mount Point</th><th>Serial (if available)</th></tr>"
    if sys.platform == "darwin":
        parsed_disks = []
        try:
            disk_info_plist_str = helpers.run_command("diskutil list -plist", check_shell=True, app_instance=app_instance)
            if disk_info_plist_str:
                try:
                    if isinstance(disk_info_plist_str, bytes):
                        disk_info_plist_str = disk_info_plist_str.decode('utf-8', errors='replace')

                    disk_plist = plistlib.loads(disk_info_plist_str.encode('utf-8'))
                    all_disks_and_partitions = disk_plist.get('AllDisksAndPartitions', [])
                    
                    for disk_entry in all_disks_and_partitions:
                        if not isinstance(disk_entry, dict):
                            app_instance.log_output(f"Warning: Skipping non-dictionary disk entry: {type(disk_entry)} - {disk_entry}")
                            continue

                        disk_name = disk_entry.get('DeviceIdentifier', 'N/A')
                        disk_size_bytes = disk_entry.get('Size', 0)
                        disk_size_gb = round(disk_size_bytes / (1024**3), 2)
                        disk_serial = "N/A"

                        if disk_entry.get('Product'):
                            serial_output = helpers.run_command(f"system_profiler SPNVMeDataType SPSerialATADataType | grep \"{disk_entry['Product']}\" -B 5 | grep \"Serial Number:\"", check_shell=True, app_instance=app_instance)
                            if serial_output:
                                serial_match = re.search(r'Serial Number: (.+)', serial_output)
                                if serial_match:
                                    disk_serial = serial_match.group(1).strip()
                            else:
                                app_instance.log_output(f"Could not get serial for {disk_name} via system_profiler.")
                        
                        parsed_disks.append(DiskInfo(
                            name=disk_name,
                            type="Physical Disk",
                            size_gb=disk_size_gb,
                            used="N/A", available="N/A",
                            filesystem="N/A", mount_point="N/A",
                            serial=disk_serial,
                            volume_name="N/A", device_identifier=disk_name
                        ))

                        if 'Partitions' in disk_entry and isinstance(disk_entry['Partitions'], list):
                            for partition in disk_entry['Partitions']:
                                if not isinstance(partition, dict):
                                    app_instance.log_output(f"Warning: Skipping non-dictionary partition: {type(partition)} - {partition}")
                                    continue
                                
                                part_name = partition.get('VolumeName', partition.get('DeviceIdentifier', 'N/A'))
                                part_size_bytes = partition.get('Size', 0)
                                part_size_gb = round(part_size_bytes / (1024**3), 2)
                                part_fs = partition.get('FilesystemType', 'N/A')
                                part_mount_point = partition.get('MountPoint', 'N/A')

                                used = "N/A"
                                avail = "N/A"
                                if part_mount_point and part_mount_point != "N/A":
                                    df_output = helpers.run_command(f"df -h '{part_mount_point}'", check_shell=True, app_instance=app_instance)
                                    if df_output and len(df_output.splitlines()) > 1:
                                        df_parts = df_output.splitlines()[1].split()
                                        if len(df_parts) > 3:
                                            used = df_parts[2]
                                            avail = df_parts[3]

                                parsed_disks.append(DiskInfo(
                                    name=part_name,
                                    type="Partition",
                                    size_gb=part_size_gb,
                                    used=used, available=avail,
                                    filesystem=part_fs, mount_point=part_mount_point,
                                    serial="N/A",
                                    volume_name=partition.get('VolumeName'), device_identifier=partition.get('DeviceIdentifier')
                                ))

                except plistlib.InvalidFileException:
                    app_instance.log_output(f"Error: diskutil list -plist output not valid. Raw output snippet: {disk_info_plist_str[:500]}...")
                    html_body += f"<tr><td colspan='7'>Error parsing diskutil output. Raw data snippet: <pre>{disk_info_plist_str[:500]}</pre></td></tr>"
                except Exception as e:
                    app_instance.log_output(f"Unexpected error parsing diskutil list: {e}")
                    html_body += f"<tr><td colspan='7'>Unexpected error parsing diskutil list.</td></tr>"

            if parsed_disks:
                for d in parsed_disks:
                    html_body += f"<tr><td>{d.name} ({d.type})</td><td>{d.size_gb} GB</td><td>{d.used}</td><td>{d.available}</td><td>{d.filesystem}</td><td>{d.mount_point}</td><td>{d.serial}</td></tr>"
            else:
                html_body += "<p>No storage devices found or processed.</p>"

        except Exception as e:
            app_instance.log_output(f"Error gathering macOS Storage details: {e}")
            html_body += f"<tr><td colspan='7'>Error gathering detailed macOS Storage info.</td></tr>"
    elif sys.platform == "win32":
        try:
            wmic_disk_output = helpers.run_command("wmic diskdrive get Caption,SerialNumber,Size /format:list", app_instance=app_instance)
            if wmic_disk_output:
                html_body += "<tr><th colspan='7'>Physical Disk Drives</th></tr>"
                current_disk = {}
                for line in wmic_disk_output.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        current_disk[key.strip()] = value.strip()
                    elif not line.strip() and current_disk:
                        size_gb = round(int(current_disk.get('Size', 0)) / (1024**3), 2)
                        html_body += f"<tr><td>{current_disk.get('Caption', 'N/A')}</td><td>{size_gb} GB</td><td>N/A</td><td>N/A</td><td>N/A</td><td>N/A</td><td>{current_disk.get('SerialNumber', 'N/A')}</td></tr>"
                        current_disk = {}
                if current_disk:
                    size_gb = round(int(current_disk.get('Size', 0)) / (1024**3), 2)
                    free_gb = round(int(current_disk.get('FreeSpace', 0)) / (1024**3), 2)
                    used_gb = round(size_gb - free_gb, 2)
                    html_body += f"<tr><td>{current_disk.get('Caption', 'N/A')}</td><td>{size_gb} GB</td><td>N/A</td><td>N/A</td><td>N/A</td><td>N/A</td><td>{current_disk.get('SerialNumber', 'N/A')}</td></tr>"

            wmic_volume_output = helpers.run_command("wmic logicaldisk get Caption,Freespace,Size,FileSystem /format:list", app_instance=app_instance)
            if wmic_volume_output:
                html_body += "<tr><th colspan='7'>Logical Disk Volumes</th></tr>"
                current_volume = {}
                for line in wmic_volume_output.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        current_volume[key.strip()] = value.strip()
                    elif not line.strip() and current_volume:
                        size_gb = round(int(current_volume.get('Size', 0)) / (1024**3), 2)
                        free_gb = round(int(current_volume.get('FreeSpace', 0)) / (1024**3), 2)
                        used_gb = round(size_gb - free_gb, 2)
                        html_body += f"<tr><td>{current_volume.get('Caption', 'N/A')}</td><td>{size_gb} GB</td><td>{used_gb} GB</td><td>{free_gb} GB</td><td>{current_volume.get('FileSystem', 'N/A')}</td><td>N/A</td><td>N/A</td></tr>"
                        current_volume = {}
                if current_volume:
                    size_gb = round(int(current_volume.get('Size', 0)) / (1024**3), 2)
                    free_gb = round(int(current_volume.get('FreeSpace', 0)) / (1024**3), 2)
                    used_gb = round(size_gb - free_gb, 2)
                    html_body += f"<tr><td>{current_volume.get('Caption', 'N/A')}</td><td>{size_gb} GB</td><td>{used_gb} GB</td><td>{free_gb} GB</td><td>{current_volume.get('FileSystem', 'N/A')}</td><td>N/A</td><td>N/A</td></tr>"

        except Exception as e:
            app_instance.log_output(f"Error gathering Windows Storage details: {e}")
            html_body += f"<tr><td colspan='7'>Error gathering detailed Windows Storage info.</td></tr>"
    html_body += """</table>"""
    html_body += """<p>For more detailed interpretations or comparisons, specialized benchmarking tools are required.</p>"""

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "System_Hardware_Report.html", 
        "System & Hardware Information Report", 
        html_body,
        browser_preference=browser_preference
    )

