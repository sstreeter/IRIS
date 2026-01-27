import plistlib
import os
import hashlib
import json
from datetime import datetime
from typing import Any, List, Dict
from ...helpers import Helpers, MockAppInstance

# Extensions to look for
DISK_IMAGE_EXTS = {'.iso', '.dmg', '.img', '.dd', '.cdr', '.vmdk', '.vmwarevm'}
# Visual Media: Raster + Vector
MEDIA_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.svg', '.ai', '.eps', '.psd', '.pdf'}

def get_partial_hash(file_path: str, chunk_size: int = 4096) -> str:
    """Read first and last chunk to create a quick signature for large files."""
    try:
        size = os.path.getsize(file_path)
        if size == 0: return "empty"
        with open(file_path, 'rb') as f:
            start = f.read(chunk_size)
            if size > chunk_size:
                f.seek(-chunk_size, 2)
                end = f.read(chunk_size)
            else:
                end = b""
            return hashlib.md5(start + end).hexdigest()
    except:
        return "error"

def format_size(size_bytes: int) -> str:
    if size_bytes == 0: return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"

def scan_user_directories(app_instance: Any) -> List[Dict[str, Any]]:
    """
    Scans user directories for both Disk Images and Media Files.
    Returns a unified list of file objects with 'category' field.
    """
    found_files = []
    
    # Directories to scan
    scan_roots = [
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Public"),
        os.path.expanduser("~/Pictures"),
        "/Applications"
    ]
    
    app_instance.log_output("Scanning user directories for disk images and media...")
    
    # Time Filter
    tr = getattr(app_instance, 'time_range', {})
    t_start = tr.get("start")
    t_end = tr.get("end")

    for root_dir in scan_roots:
        if not os.path.exists(root_dir): continue
        
        for root, dirs, files in os.walk(root_dir, topdown=True):
            # Skip hidden dirs, Library, etc.
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('Library', 'node_modules', '.git')]
            
            for name in files:
                if name.startswith('.'): continue
                ext = os.path.splitext(name)[1].lower()
                
                category = None
                if ext in DISK_IMAGE_EXTS:
                    category = "disk_image"
                elif ext in MEDIA_EXTS:
                    category = "media_file"
                
                if category:
                    full_path = os.path.join(root, name)
                    try:
                        stats = os.stat(full_path)
                        # Filter by Time
                        if t_start or t_end:
                            mtime_dt = datetime.fromtimestamp(stats.st_mtime)
                            if t_start and mtime_dt < t_start: continue
                            if t_end and mtime_dt > t_end: continue
                            
                        item = {
                            "name": name,
                            "path": full_path,
                            "size": stats.st_size,
                            "mtime": stats.st_mtime,
                            "ext": ext,
                            "category": category,
                            "dup_group": None
                        }
                        found_files.append(item)
                    except: pass
                    
    return found_files

def analyze_duplicates(files: List[Dict[str, Any]]):
    """Mark duplicates based on Size + Partial Hash."""
    if not files: return
    # 1. Group by Size
    by_size = {}
    for f in files:
        if f['category'] != 'disk_image': continue # skip media for now to save time
        s = f['size']
        if s not in by_size: by_size[s] = []
        by_size[s].append(f)
        
    # 2. For same size, check partial hash
    for size, sublist in by_size.items():
        if len(sublist) > 1:
            by_hash = {}
            for f in sublist:
                ph = get_partial_hash(f['path'])
                if ph not in by_hash: by_hash[ph] = []
                by_hash[ph].append(f)
            
            for ph, dupes in by_hash.items():
                if len(dupes) > 1:
                    grp_id = ph[:8]
                    for d in dupes:
                        d['dup_group'] = grp_id

def generate_images_report(app_instance: Any, helpers: Helpers, browser_preference: str = "System Default"):
    """
    Reports on Disk Images & Visual Media using a Client-Side SPA approach.
    Embeds data as JSON and uses JS for dynamic Rendering, Sorting, Filtering, and Pagination.
    """
    app_instance.log_output("\n--- Generating Advanced Filesystem Artifacts Report ---")
    
    # 1. Gather Data
    all_files = scan_user_directories(app_instance)
    analyze_duplicates(all_files)
    
    # Serialize to JSON (Need to make sure keys are safe)
    # We add a 'formatted_size' and 'formatted_date' for easier JS display initially
    for f in all_files:
        f['formatted_size'] = format_size(f['size'])
        f['formatted_date'] = datetime.fromtimestamp(f['mtime']).strftime("%Y-%m-%d %H:%M")
        # Add file:// protocol for local access in the report (only works if opened locally)
        f['file_url'] = f"file://{f['path']}"
        
    json_data = json.dumps(all_files)

    # 2. HTML SPA Shell (V2)
    html_body = f"""
    <div id="app" class="report-app">
        
        <!-- Sidebar Preview Panel -->
        <div id="sidebar" class="sidebar">
            <div class="sidebar-header">
                <h3>Details</h3>
                <button onclick="app.closeSidebar()">×</button>
            </div>
            <div id="sidebarContent" class="sidebar-content">
                <div class="placeholder-text">Select a file to view details</div>
            </div>
            <div class="sidebar-actions" id="sidebarActions" style="display:none;">
                <a href="#" target="_blank" id="btnOpen" class="btn-action primary">Open File</a>
                <a href="#" target="_blank" id="btnReveal" class="btn-action">Show in Finder</a>
            </div>
        </div>

        <!-- Main Content -->
        <div class="main-layout">
            <!-- Toolbar -->
            <div class="sticky-toolbar">
                <!-- Row 1: Search & View -->
                <div class="toolbar-row">
                    <div class="search-box">
                        <span class="search-icon">🔍</span>
                        <input type="text" id="searchInput" placeholder="Search filenames..." onkeyup="app.updateFilter()">
                    </div>
                    <div class="view-toggles">
                        <button class="btn-toggle active" onclick="app.setView('grid')" id="btn-grid">Grid</button>
                        <button class="btn-toggle" onclick="app.setView('list')" id="btn-list">List</button>
                        <button class="btn-toggle" onclick="app.setView('compact')" id="btn-compact">Table</button>
                    </div>
                </div>
                
                <!-- Row 2: Advanced Filters -->
                <div class="toolbar-row wrap-row">
                    <div class="filter-group">
                        <label>Size:</label>
                        <select id="sizeFilter" onchange="app.updateFilter()">
                            <option value="all">Any Size</option>
                            <option value="small">Small (<1MB)</option>
                            <option value="medium">Medium (1MB-100MB)</option>
                            <option value="large">Large (>100MB)</option>
                            <option value="huge">Huge (>1GB)</option>
                        </select>
                    </div>
                    
                    <div class="filter-group">
                        <label>Type:</label>
                        <select id="typeFilter" onchange="app.updateFilter()">
                            <option value="all">All Types</option>
                            <!-- Populated by JS -->
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>Date:</label>
                        <select id="dateFilter" onchange="app.updateFilter()">
                            <option value="all">Any Time</option>
                            <option value="today">Today</option>
                            <option value="week">Last 7 Days</option>
                            <option value="month">Last 30 Days</option>
                        </select>
                    </div>

                    <div class="filter-group checkboxes">
                        <label><input type="checkbox" id="filterDisk" checked onchange="app.updateFilter()"> Disk Images</label>
                        <label><input type="checkbox" id="filterMedia" checked onchange="app.updateFilter()"> Media</label>
                    </div>
                </div>

                <!-- Row 3: Sort & Pagination Status -->
                <div class="toolbar-row secondary">
                    <div class="sort-controls">
                        <label>Sort:</label>
                        <select id="sortField" onchange="app.updateSort()">
                            <option value="size_desc" selected>Size (Largest ⬇)</option>
                            <option value="size_asc">Size (Smallest ⬆)</option>
                            <option value="date_desc">Date (Newest ⬇)</option>
                            <option value="date_asc">Date (Oldest ⬆)</option>
                            <option value="type">Type (Ext)</option>
                            <option value="name">Name</option>
                        </select>
                    </div>
                    
                    <div class="pagination-controls">
                        <button onclick="app.prevPage()" id="btnPrev">◀</button>
                        <span id="pageInfo">Page 1 of 1</span>
                        <button onclick="app.nextPage()" id="btnNext">▶</button>
                    </div>
                    
                    <div class="status-bar" id="statusBar">Loading...</div>
                </div>
            </div>

            <!-- Content Area -->
            <div id="contentArea" class="content-area view-grid"></div>
        </div>
    </div>

    <style>
        :root {{ --primary: #007bff; --bg: #f8f9fa; --border: #dee2e6; --text: #333; --sidebar-w: 300px; }}
        body {{ margin: 0; font-family: -apple-system, system-ui, sans-serif; background: #fff; color: var(--text); overflow: hidden; height: 100vh; }}
        
        .report-app {{ display: flex; height: 100vh; }}
        
        /* Sidebar */
        .sidebar {{ width: var(--sidebar-w); background: #fff; border-right: 1px solid var(--border); display: flex; flex-direction: column; z-index: 200; box-shadow: 2px 0 5px rgba(0,0,0,0.05); transition: transform 0.3s; }}
        .sidebar.closed {{ transform: translateX(calc(-1 * var(--sidebar-w))); margin-right: calc(-1 * var(--sidebar-w)); }}
        .sidebar-header {{ padding: 15px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: #f1f1f1; }}
        .sidebar-header h3 {{ margin: 0; font-size: 16px; }}
        .sidebar-content {{ flex: 1; overflow-y: auto; padding: 20px; }}
        .placeholder-text {{ color: #999; text-align: center; margin-top: 50px; font-style: italic; }}
        .sidebar-actions {{ padding: 15px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 10px; background: #f9f9f9; }}
        .btn-action {{ display: block; text-align: center; padding: 10px; border-radius: 4px; text-decoration: none; border: 1px solid var(--border); background: #fff; color: #333; }}
        .btn-action.primary {{ background: var(--primary); color: #fff; border: none; }}
        .btn-action:hover {{ opacity: 0.9; }}

        /* Main Layout */
        .main-layout {{ flex: 1; display: flex; flex-direction: column; min-width: 0; }}
        
        /* Toolbar */
        .sticky-toolbar {{ background: #fff; border-bottom: 1px solid var(--border); padding: 10px 20px; z-index: 100; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }}
        .toolbar-row {{ display: flex; align-items: center; gap: 15px; margin-bottom: 8px; }}
        .wrap-row {{ flex-wrap: wrap; }}
        .toolbar-row.secondary {{ margin-bottom: 0; font-size: 13px; color: #666; justify-content: space-between; }}
        
        /* Inputs */
        .search-box {{ flex: 1; position: relative; min-width: 200px; }}
        .search-box input {{ width: 100%; padding: 6px 10px 6px 30px; border: 1px solid #ccc; border-radius: 4px; }}
        .search-icon {{ position: absolute; left: 8px; top: 50%; transform: translateY(-50%); opacity: 0.5; }}
        
        .filter-group {{ display: flex; align-items: center; gap: 5px; font-size: 13px; }}
        .filter-group select {{ padding: 4px; border-radius: 4px; border: 1px solid #ccc; max-width: 150px; }}
        .checkboxes label {{ margin-right: 10px; cursor: pointer; }}

        /* View Toggles */
        .view-toggles {{ display: flex; border: 1px solid #ccc; border-radius: 4px; overflow: hidden; }}
        .btn-toggle {{ border: none; background: #f0f0f0; padding: 6px 12px; cursor: pointer; border-right: 1px solid #ccc; font-size: 13px; }}
        .btn-toggle:last-child {{ border-right: none; }}
        .btn-toggle.active {{ background: var(--primary); color: #fff; }}

        /* Pagination */
        .pagination-controls {{ display: flex; align-items: center; gap: 10px; }}
        .pagination-controls button {{ border: 1px solid #ccc; background: #fff; border-radius: 4px; padding: 2px 8px; cursor: pointer; }}
        .pagination-controls button:disabled {{ opacity: 0.5; cursor: default; }}
        
        /* Content Area */
        .content-area {{ flex: 1; overflow-y: auto; padding: 20px; background: #fafafa; }}
        
        /* Grid View */
        .view-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; align-content: start; }}
        .card {{ background: #fff; border: 1px solid #eee; border-radius: 6px; overflow: hidden; transition: 0.2s; cursor: pointer; position: relative; }}
        .card.selected {{ border-color: var(--primary); box-shadow: 0 0 0 3px rgba(0,123,255,0.2); }}
        .card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.05); }}
        .card-thumb {{ height: 100px; background: #eee; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
        .card-thumb img {{ width: 100%; height: 100%; object-fit: cover; }}
        .card-body {{ padding: 8px; text-align: center; }}
        .card-title {{ font-size: 12px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .card-meta {{ font-size: 11px; color: #888; margin-top: 2px; }}

        /* List/Compact Views */
        .view-list, .view-compact {{ display: block; }}
        .list-row {{ display: flex; align-items: center; padding: 8px; background: #fff; border-bottom: 1px solid #eee; cursor: pointer; }}
        .list-row:hover {{ background: #f8f9fa; }}
        .list-row.selected {{ background: #e8f0fe; }}
        .list-icon {{ width: 40px; height: 40px; background: #eee; margin-right: 10px; display: flex; align-items: center; justify-content: center; border-radius: 4px; overflow: hidden; flex-shrink: 0; }}
        .list-icon img {{ width: 100%; height: 100%; object-fit: cover; }}
        
        .compact-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
        .compact-table th {{ text-align: left; padding: 8px; background: #f1f1f1; position: sticky; top: 0; }}
        .compact-table td {{ padding: 6px 8px; border-bottom: 1px solid #eee; cursor: pointer; }}
        .compact-table tr:hover {{ background: #f8f9fa; }}
        .compact-table tr.selected {{ background: #e8f0fe; }}
    </style>

    <script>
    window.fileData = {json_data};
    
    const APP = {{
        data: [],
        filtered: [],
        view: 'grid',
        sort: 'size_desc',
        search: '',
        filters: {{ size:'all', type:'all', date:'all', disk:true, media:true }},
        page: 1,
        pageSize: 100,
        selectedId: null,

        init: function() {{
            this.data = window.fileData.map((d, i) => ({{...d, id: i}})); // Add ID
            this.populateTypes();
            this.applyFilters();
        }},

        populateTypes: function() {{
            const types = new Set(this.data.map(d => d.ext));
            const sel = document.getElementById('typeFilter');
            Array.from(types).sort().forEach(t => {{
                const opt = document.createElement('option');
                opt.value = t;
                opt.textContent = t;
                sel.appendChild(opt);
            }});
        }},

        updateFilter: function() {{
            this.search = document.getElementById('searchInput').value.toLowerCase();
            this.filters.size = document.getElementById('sizeFilter').value;
            this.filters.type = document.getElementById('typeFilter').value;
            this.filters.date = document.getElementById('dateFilter').value;
            this.filters.disk = document.getElementById('filterDisk').checked;
            this.filters.media = document.getElementById('filterMedia').checked;
            this.page = 1;
            this.applyFilters();
        }},

        updateSort: function() {{
            this.sort = document.getElementById('sortField').value;
            this.page = 1;
            this.sortData();
            this.render();
        }},

        setView: function(v) {{
            this.view = v;
            document.querySelectorAll('.btn-toggle').forEach(b => b.classList.remove('active'));
            document.getElementById('btn-'+v).classList.add('active');
            document.getElementById('contentArea').className = 'content-area view-' + v;
            this.render();
        }},

        applyFilters: function() {{
            const now = new Date();
            this.filtered = this.data.filter(item => {{
                // Category
                if (item.category === 'disk_image' && !this.filters.disk) return false;
                if (item.category === 'media_file' && !this.filters.media) return false;
                
                // Search
                if (this.search && !item.name.toLowerCase().includes(this.search)) return false;
                
                // Type
                if (this.filters.type !== 'all' && item.ext !== this.filters.type) return false;

                // Size
                if (this.filters.size !== 'all') {{
                    const s = item.size;
                    if (this.filters.size === 'small' && s >= 1048576) return false;
                    if (this.filters.size === 'medium' && (s < 1048576 || s >= 104857600)) return false;
                    if (this.filters.size === 'large'  && (s < 104857600 || s >= 1073741824)) return false;
                    if (this.filters.size === 'huge'   && s < 1073741824) return false;
                }}

                // Date
                if (this.filters.date !== 'all') {{
                    const ageDays = (now.getTime() / 1000 - item.mtime) / 86400;
                    if (this.filters.date === 'today' && ageDays > 1) return false;
                    if (this.filters.date === 'week' && ageDays > 7) return false;
                    if (this.filters.date === 'month' && ageDays > 30) return false;
                }}
                
                return true;
            }});
            
            this.sortData();
            this.render();
        }},

        sortData: function() {{
            const s = this.sort;
            this.filtered.sort((a,b) => {{
                if (s === 'size_desc') return b.size - a.size;
                if (s === 'size_asc') return a.size - b.size;
                if (s === 'date_desc') return b.mtime - a.mtime;
                if (s === 'date_asc') return a.mtime - b.mtime;
                if (s === 'name') return a.name.localeCompare(b.name);
                if (s === 'type') return a.ext.localeCompare(b.ext);
                return 0;
            }});
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
            this.render(); // Re-render to show selected state
            this.renderSidebar(this.data[id]);
        }},
        
        closeSidebar: function() {{
            document.getElementById('sidebar').classList.add('closed');
        }},

        renderSidebar: function(item) {{
            const sb = document.getElementById('sidebar');
            const content = document.getElementById('sidebarContent');
            const actions = document.getElementById('sidebarActions');
            
            sb.classList.remove('closed');
            actions.style.display = 'flex';
            
            const icon = this.getIcon(item);
            let thumbInfo = '';
            if (icon.type === 'img') thumbInfo = `<img src="${{icon.src}}" style="max-width:100%; border-radius:4px; margin-bottom:15px;">`;
            else thumbInfo = `<div style="font-size:3em; color:#ccc; text-align:center; padding:20px;">${{icon.val}}</div>`;

            content.innerHTML = `
                ${{thumbInfo}}
                <div style="font-weight:bold; word-break:break-all;">${{item.name}}</div>
                <div style="font-size:0.9em; color:#666; margin:5px 0 15px;">${{item.formatted_size}} • ${{item.ext}}</div>
                
                <div style="font-size:0.85em; display:grid; grid-template-columns:auto 1fr; gap:5px 10px;">
                    <strong>Path:</strong> <span style="word-break:break-all;">${{item.path}}</span>
                    <strong>Date:</strong> <span>${{item.formatted_date}}</span>
                    <strong>Type:</strong> <span>${{item.category}}</span>
                </div>
            `;
            
            document.getElementById('btnOpen').href = item.file_url;
            document.getElementById('btnReveal').href = item.file_url; // Browse logic usually OS specific, linking file helps
        }},

        render: function() {{
            const container = document.getElementById('contentArea');
            container.innerHTML = '';
            
            // Pagination Slice
            const start = (this.page - 1) * this.pageSize;
            const pageData = this.filtered.slice(start, start + this.pageSize);
            
            // Update Status Controls
            const maxPage = Math.ceil(this.filtered.length / this.pageSize) || 1;
            document.getElementById('pageInfo').textContent = `Page ${{this.page}} of ${{maxPage}}`;
            document.getElementById('statusBar').textContent = `Found ${{this.filtered.length}} items (Total: ${{this.data.length}})`;
            document.getElementById('btnPrev').disabled = (this.page === 1);
            document.getElementById('btnNext').disabled = (this.page === maxPage);

            let html = '';
            if (this.view === 'compact') {{
                html = `<table class="compact-table"><thead><tr><th>Name</th><th>Size</th><th>Date</th><th>Path</th></tr></thead><tbody>`;
                pageData.forEach(item => {{
                    const sel = item.id === this.selectedId ? 'selected' : '';
                    const dup = item.dup_group ? 'style="background:#fff3cd"' : '';
                    html += `<tr class="${{sel}}" ${{dup}} onclick="app.selectItem(${{item.id}})">
                        <td>${{item.name}}</td><td>${{item.formatted_size}}</td><td>${{item.formatted_date}}</td><td>${{item.path}}</td>
                    </tr>`;
                }});
                html += '</tbody></table>';
            }} else {{
                pageData.forEach(item => {{
                    const sel = item.id === this.selectedId ? 'selected' : '';
                    const icon = this.getIcon(item);
                    let thumb = (icon.type === 'img') ? `<img src="${{icon.src}}" loading="lazy">` : `<div class="no-preview" style="font-size:1.2em; color:#ccc;">${{icon.val}}</div>`;
                    
                    if (this.view === 'grid') {{
                        html += `
                        <div class="card ${{sel}}" onclick="app.selectItem(${{item.id}})">
                            <div class="card-thumb">${{thumb}}</div>
                            <div class="card-body">
                                <div class="card-title">${{item.name}}</div>
                                <div class="card-meta">${{item.formatted_size}}</div>
                            </div>
                        </div>`;
                    }} else {{
                        html += `
                        <div class="list-row ${{sel}}" onclick="app.selectItem(${{item.id}})">
                            <div class="list-icon">${{thumb}}</div>
                            <div style="flex:1; min-width:0;">
                                <div style="font-weight:500;">${{item.name}}</div>
                                <div style="font-size:11px; color:#888;">${{item.path}}</div>
                            </div>
                            <div style="flex-shrink:0; width:120px; text-align:right; font-size:12px;">${{item.formatted_size}}</div>
                        </div>`;
                    }}
                }});
            }}
            container.innerHTML = html;
        }},
        
        getIcon: function(item) {{
             const ext = item.ext;
             if (['.jpg','.jpeg','.png','.gif','.webp','.svg'].includes(ext)) return {{type:'img', src: item.file_url}};
             return {{type:'text', val: ext.replace('.','').toUpperCase().substring(0,4)}};
        }}
    }};
    
    document.addEventListener('DOMContentLoaded', () => APP.init());
    window.app = APP;
    </script>
    """
    
    helpers.generate_report_html(
        app_instance, 
        app_instance.suspect_computer_name, 
        "Images_Report.html", 
        "Advanced Disk & Media Artifacts", 
        html_body,
        browser_preference=browser_preference
    )
