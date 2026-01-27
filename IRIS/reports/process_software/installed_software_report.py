import json
import sys
from datetime import datetime
from typing import Any

from ...helpers import MockAppInstance, Helpers

def generate_installed_software_report(app_instance: Any, helpers: Any, browser_preference: str = "System Default"):
    """
    Gathers and reports installed software using rich system_profiler data on macOS.
    Implements V2 Client-Side UI with Filtering, Sorting, and Details.
    """
    app_instance.log_output("\n--- Generating Installed Software Report (V2) ---")
    
    apps_data = []

    if sys.platform == "darwin":
        cmd = ["system_profiler", "SPApplicationsDataType", "-json"]
        raw_json = helpers.run_command(cmd, app_instance=app_instance)
        
        if raw_json:
            try:
                data = json.loads(raw_json)
                apps = data.get("SPApplicationsDataType", [])
                
                for app in apps:
                    # Parse interesting fields
                    name = app.get("_name", "Unknown")
                    version = app.get("version", "N/A")
                    vendor = "Unknown"
                    if "obtained_from" in app:
                        src = app.get("obtained_from", "")
                        if src == "apple": vendor = "Apple"
                        elif src == "mac_app_store": vendor = "App Store"
                        elif src == "identified_developer": vendor = "Detected Developer"
                        else: vendor = src.title() if src else "Unknown"
                        
                    path = app.get("path", "")
                    arch = app.get("arch_kind", "Unknown") # arch_arm_i64 etc
                    last_mod = app.get("lastModified", "")
                    
                    # Formatting Date
                    fmt_date = ""
                    try:
                        # 2025-11-22T13:49:28Z
                        dt = datetime.strptime(last_mod, "%Y-%m-%dT%H:%M:%SZ")
                        fmt_date = dt.strftime("%Y-%m-%d")
                    except:
                        fmt_date = last_mod

                    # Architecture Simplification
                    if "arm" in arch or "64" in arch: arch_simple = "64-bit"
                    else: arch_simple = "32-bit (Legacy)"
                    
                    # Smart Icon Logic
                    n_lower = name.lower()
                    v_lower = vendor.lower()
                    icon = "📦" # Default
                    
                    if any(x in n_lower for x in ['adobe', 'photoshop', 'lightroom', 'figma', 'sketch', 'final cut', 'imovie', 'photos']): icon = "🎨"
                    elif any(x in n_lower for x in ['xcode', 'visual studio', 'vscode', 'python', 'terminal', 'iterm', 'docker', 'git']): icon = "🔨"
                    elif any(x in n_lower for x in ['chrome', 'firefox', 'safari', 'edge', 'brave', 'arc', 'opera']): icon = "🌐"
                    elif any(x in n_lower for x in ['word', 'excel', 'powerpoint', 'pages', 'numbers', 'keynote', 'office', 'notes']): icon = "📄"
                    elif any(x in n_lower for x in ['slack', 'zoom', 'teams', 'discord', 'mail', 'outlook', 'signal', 'whatsapp']): icon = "💬"
                    elif any(x in n_lower for x in ['antivirus', 'mcafee', 'norton', 'sophos', 'malwarebytes', 'little snitch', 'lulu', 'security']): icon = "🛡️"
                    elif any(x in n_lower for x in ['settings', 'preferences', 'activity monitor', 'console', 'disk utility']): icon = "⚙️"
                    elif vendor == "Apple": icon = "🍎"

                    apps_data.append({
                        "name": name,
                        "version": version,
                        "vendor_raw": vendor,
                        "vendor_group": "Apple" if vendor in ["Apple", "App Store"] else "3rd Party",
                        "path": path,
                        "arch": arch_simple,
                        "date": fmt_date,
                        "icon": icon,
                        "info": app.get("info", "") 
                    })
                    
            except Exception as e:
                app_instance.log_output(f"Error parsing system_profiler JSON: {e}")
                # Fallback handled by empty list
    else:
        # Simple fallback for non-macOS
        pass

    # Serialize for JS
    json_payload = json.dumps(apps_data)

    # HTML Shell with V2 UI
    html_body = f"""
    <div id="app" class="report-app">
        <!-- Sidebar -->
        <div id="sidebar" class="sidebar">
            <div class="sidebar-header">
                <h3>App Details</h3>
                <button onclick="app.closeSidebar()">×</button>
            </div>
            <div id="sidebarContent" class="sidebar-content">
                <div class="placeholder-text">Select an application</div>
            </div>
        </div>

        <!-- Main Layout -->
        <div class="main-layout">
            <!-- Toolbar -->
            <div class="sticky-toolbar">
                <div class="toolbar-row">
                    <div class="search-box">
                        <span class="search-icon">🔍</span>
                        <input type="text" id="searchInput" placeholder="Search apps..." onkeyup="app.updateFilter()">
                    </div>
                </div>
                
                <div class="toolbar-row wrap-row">
                    <div class="filter-group checkboxes">
                        <label><input type="checkbox" id="filterApple" checked onchange="app.updateFilter()"> Apple/System</label>
                        <label><input type="checkbox" id="filter3rd" checked onchange="app.updateFilter()"> 3rd Party</label>
                        <label>
                            <select id="filterArch" onchange="app.updateFilter()" style="padding:2px; border-radius:3px; border:1px solid #ccc;">
                                <option value="all">Any Arch</option>
                                <option value="64">64-bit Only</option>
                                <option value="32">32-bit Only</option>
                            </select>
                        </label>
                    </div>
                    <div class="status-bar" id="statusBar">Loading...</div>
                </div>

                <div class="toolbar-row secondary">
                    <div class="sort-controls">
                         <button onclick="app.resetSort()" style="font-size:11px; padding:2px 6px;">Reset Sort</button>
                    </div>
                    <div class="pagination-controls">
                        <button onclick="app.prevPage()" id="btnPrev">◀</button>
                        <span id="pageInfo">Page 1</span>
                        <button onclick="app.nextPage()" id="btnNext">▶</button>
                    </div>
                </div>
            </div>

            <!-- Content Table -->
            <div id="contentArea" class="content-area">
                <table class="app-table">
                    <thead>
                        <tr>
                            <th style="width:50px; text-align:center;">#</th>
                            <th onclick="app.setSort('name')" class="sortable">Name <span id="sort-name"></span></th>
                            <th onclick="app.setSort('version')" class="sortable">Version <span id="sort-version"></span></th>
                            <th onclick="app.setSort('vendor')" class="sortable">Vendor <span id="sort-vendor"></span></th>
                            <th onclick="app.setSort('arch')" class="sortable">Arch <span id="sort-arch"></span></th>
                            <th onclick="app.setSort('date_desc')" class="sortable">Updated <span id="sort-date_desc"></span></th>
                        </tr>
                    </thead>
                    <tbody id="tableBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <style>
        :root {{ --primary: #007bff; --bg: #f8f9fa; --border: #dee2e6; --text: #333; --sidebar-w: 300px; }}
        body {{ margin: 0; font-family: -apple-system, system-ui, sans-serif; background: #fff; color: var(--text); overflow: hidden; height: 100vh; }}
        
        .report-app {{ display: flex; height: 100vh; }}
        
        /* Sidebar */
        .sidebar {{ width: var(--sidebar-w); background: #fff; border-right: 1px solid var(--border); display: flex; flex-direction: column; z-index: 200; box-shadow: 2px 0 5px rgba(0,0,0,0.05); transition: transform 0.3s; transform: translateX(calc(-1 * var(--sidebar-w))); margin-right: calc(-1 * var(--sidebar-w)); }}
        .sidebar.open {{ transform: translateX(0); margin-right: 0; }}
        .sidebar-header {{ padding: 15px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: #f1f1f1; }}
        .sidebar-header h3 {{ margin: 0; font-size: 16px; }}
        .sidebar-content {{ flex: 1; overflow-y: auto; padding: 20px; word-wrap: break-word; }}
        .placeholder-text {{ color: #999; text-align: center; margin-top: 50px; font-style: italic; }}

        /* Main Layout */
        .main-layout {{ flex: 1; display: flex; flex-direction: column; min-width: 0; }}
        
        /* Toolbar */
        .sticky-toolbar {{ background: #fff; border-bottom: 1px solid var(--border); padding: 10px 20px; z-index: 100; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }}
        .toolbar-row {{ display: flex; align-items: center; gap: 15px; margin-bottom: 8px; }}
        .wrap-row {{ flex-wrap: wrap; justify-content: space-between; }}
        .toolbar-row.secondary {{ margin-bottom: 0; font-size: 13px; color: #666; justify-content: space-between; }}
        
        .search-box {{ flex: 1; position: relative; }}
        .search-box input {{ width: 100%; padding: 6px 10px 6px 30px; border: 1px solid #ccc; border-radius: 4px; }}
        .search-icon {{ position: absolute; left: 8px; top: 50%; transform: translateY(-50%); opacity: 0.5; }}
        
        .checkboxes label {{ margin-right: 15px; cursor: pointer; font-size: 13px; display:inline-flex; align-items:center; gap:5px; }}
        
        /* Table */
        .content-area {{ flex: 1; overflow-y: auto; padding: 0; background: #fff; }}
        .app-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        .app-table th {{ text-align: left; padding: 10px 15px; background: #f8f9fa; position: sticky; top: 0; border-bottom: 1px solid #ddd; z-index: 10; cursor: pointer; user-select: none; }}
        .app-table th:hover {{ background: #e9ecef; }}
        .app-table td {{ padding: 8px 15px; border-bottom: 1px solid #eee; cursor: pointer; }}
        .app-table tr:hover {{ background: #f1faff; }}
        .app-table tr.selected {{ background: #e8f0fe; }}
        
        .sortable {{ position: relative; padding-right: 20px !important; }}

        .badge {{ padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 500; }}
        .badge.vendor-apple {{ background: #e2e3e5; color: #383d41; }}
        .badge.vendor-3rd {{ background: #d1e7dd; color: #0f5132; }}
        .badge.arch-32 {{ background: #f8d7da; color: #842029; }}

        .app-icon {{ font-size: 16px; margin-right: 8px; }}
        .row-num {{ color: #999; font-size: 12px; text-align: center; width: 30px; }}
    </style>

    <script>
    window.appData = {json_payload};
    
    const APP = {{
        data: [],
        filtered: [],
        sortField: 'name',
        sortDesc: false, 
        search: '',
        filters: {{ apple: true, third: true, arch: 'all' }},
        page: 1,
        pageSize: 100,
        selectedId: null,

        init: function() {{
            this.data = window.appData.map((d, i) => ({{...d, id: i}}));
            this.applyFilters();
        }},

        updateFilter: function() {{
            this.search = document.getElementById('searchInput').value.toLowerCase();
            this.filters.apple = document.getElementById('filterApple').checked;
            this.filters.third = document.getElementById('filter3rd').checked;
            this.filters.arch = document.getElementById('filterArch').value;
            this.page = 1;
            this.applyFilters();
        }},
        
        setSort: function(field) {{
            if (this.sortField === field) {{
                this.sortDesc = !this.sortDesc;
            }} else {{
                this.sortField = field;
                this.sortDesc = false;
                // Special default for date: usually want descending first
                if (field === 'date_desc') this.sortDesc = false; 
            }}
            this.sortData();
            this.render();
        }},
        
        resetSort: function() {{
            this.sortField = 'name';
            this.sortDesc = false;
            this.sortData();
            this.render();
        }},

        applyFilters: function() {{
            this.filtered = this.data.filter(item => {{
                // Search
                if (this.search && !item.name.toLowerCase().includes(this.search)) return false;
                
                // Arch Filter
                if (this.filters.arch === '32' && !item.arch.includes("32")) return false;
                if (this.filters.arch === '64' && !item.arch.includes("64")) return false;

                // Standard Vendor Filters
                if (item.vendor_group === 'Apple' && !this.filters.apple) return false;
                if (item.vendor_group === '3rd Party' && !this.filters.third) return false;
                
                return true;
            }});
            
            this.sortData();
            this.render();
        }},

        sortData: function() {{
            const s = this.sortField;
            const d = this.sortDesc ? -1 : 1;
            
            this.filtered.sort((a, b) => {{
                let valA, valB;
                
                if (s === 'name') {{ valA = a.name.toLowerCase(); valB = b.name.toLowerCase(); }}
                else if (s === 'version') {{ valA = a.version; valB = b.version; }}
                else if (s === 'vendor') {{ valA = a.vendor_raw.toLowerCase(); valB = b.vendor_raw.toLowerCase(); }}
                else if (s === 'arch') {{ valA = a.arch; valB = b.arch; }}
                else if (s === 'date_desc') {{ 
                    valA = a.date; valB = b.date;
                }}

                if (valA < valB) return -1 * d;
                if (valA > valB) return 1 * d;
                return 0;
            }});
            
            // Update Header Icons
            document.querySelectorAll('th span').forEach(sp => sp.textContent = '');
            const activeSpan = document.getElementById('sort-' + s);
            if (activeSpan) activeSpan.textContent = this.sortDesc ? '▼' : '▲';
        }},

        nextPage: function() {{
             const max = Math.ceil(this.filtered.length / this.pageSize);
             if (this.page < max) {{ this.page++; this.render(); }}
        }},
        
        prevPage: function() {{
             if (this.page > 1) {{ this.page--; this.render(); }}
        }},

        selectItem: function(id) {{
            this.selectedId = id;
            this.render(); 
            this.renderSidebar(this.data[id]);
        }},
        
        closeSidebar: function() {{
            document.getElementById('sidebar').classList.remove('open');
            this.selectedId = null; 
            this.render();
        }},

        renderSidebar: function(item) {{
            const sb = document.getElementById('sidebar');
            const content = document.getElementById('sidebarContent');
            
            sb.classList.add('open');
            
            content.innerHTML = `
                <div style="text-align:center; font-size:48px; margin-bottom:10px;">${{item.icon}}</div>
                <h2 style="margin-top:0; text-align:center;">${{item.name}}</h2>
                <div style="font-size:1.1em; color:#666; margin-bottom:20px; text-align:center;">Version ${{item.version}}</div>
                
                <div style="display:grid; grid-template-columns:auto 1fr; gap:10px; font-size:13px;">
                    <strong>Vendor:</strong> <span>${{item.vendor_raw}}</span>
                    <strong>Arch:</strong> <span>${{item.arch}}</span>
                    <strong>Updated:</strong> <span>${{item.date}}</span>
                </div>
                
                <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
                
                <div style="font-size:12px;">
                    <strong>Path:</strong><br>
                    <code style="background:#f5f5f5; padding:2px 5px; display:block; margin-top:5px; word-break:break-all;">${{item.path}}</code>
                </div>
            `;
        }},

        render: function() {{
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            
            // Pagination
            const start = (this.page - 1) * this.pageSize;
            const pageData = this.filtered.slice(start, start + this.pageSize);
            
            // Status
            const maxPage = Math.ceil(this.filtered.length / this.pageSize) || 1;
            document.getElementById('pageInfo').textContent = `Page ${{this.page}} of ${{maxPage}}`;
            document.getElementById('statusBar').textContent = `Found ${{this.filtered.length}} apps (Total: ${{this.data.length}})`;
            document.getElementById('btnPrev').disabled = (this.page === 1);
            document.getElementById('btnNext').disabled = (this.page === maxPage);

            let html = '';
            pageData.forEach((item, index) => {{
                const sel = item.id === this.selectedId ? 'selected' : '';
                const vendorClass = item.vendor_group === 'Apple' ? 'vendor-apple' : 'vendor-3rd';
                const archClass = item.arch.includes('32') ? 'arch-32' : '';
                const rowNum = start + index + 1;
                
                html += `
                <tr class="${{sel}}" onclick="app.selectItem(${{item.id}})">
                    <td class="row-num">${{rowNum}}</td>
                    <td style="font-weight:500;"><span class="app-icon">${{item.icon}}</span> ${{item.name}}</td>
                    <td>${{item.version}}</td>
                    <td><span class="badge ${{vendorClass}}">${{item.vendor_raw}}</span></td>
                    <td><span class="${{archClass}}">${{item.arch}}</span></td>
                    <td style="color:#666;">${{item.date}}</td>
                </tr>`;
            }});
            tbody.innerHTML = html;
        }}
    }};
    
    document.addEventListener('DOMContentLoaded', () => APP.init());
    window.app = APP;
    </script>
    """

    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Installed_Software_Report.html", 
        "Installed Application Inventory", 
        html_body,
        browser_preference=browser_preference
    )
