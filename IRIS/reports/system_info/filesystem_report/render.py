from typing import Any
from IRIS.helpers import Helpers


def get_html_body(json_data: str) -> str:
    return f"""
    <div id="app" class="report-app">
        
        <!-- Lightbox Overlay -->
        <div id="lightbox" class="lightbox" onclick="app.closeLightbox()">
            <img id="lightboxImg" src="" onclick="event.stopPropagation()">
            <button class="lightbox-close" onclick="app.closeLightbox()">×</button>
        </div>

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
                    
                    <div class="filter-group" id="zoomControl">
                        <label>Zoom:</label>
                        <input type="range" id="zoomSlider" min="100" max="400" value="160" step="10" style="width:100px" oninput="app.updateZoom(this.value)">
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
        :root {{ --primary: #007bff; --bg: #f8f9fa; --border: #dee2e6; --text: #333; --sidebar-w: 320px; --grid-size: 160px; }}
        
        /* Override template body styles for full-height app */
        body {{ 
            margin: 0 !important; 
            padding: 0 !important;
            font-family: -apple-system, system-ui, sans-serif; 
            background: #fff !important; 
            color: var(--text); 
            overflow: hidden; 
            height: 100vh; 
        }}
        
        /* Override template container to not interfere */
        .container {{
            max-width: none !important;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            border-radius: 0 !important;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        
        /* Hide template headers - they're redundant with our toolbar */
        .container > h1,
        .container > p {{
            display: none;
        }}
        
        .report-app {{ 
            display: flex; 
            height: 100vh; 
            flex: 1;
        }}
        
        /* Lightbox */
        .lightbox {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 1000; display: none; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.2s; }}
        .lightbox.active {{ display: flex; opacity: 1; }}
        .lightbox img {{ max-width: 95%; max-height: 95%; box-shadow: 0 0 20px rgba(0,0,0,0.5); cursor: default; }}
        .lightbox-close {{ position: absolute; top: 20px; right: 20px; font-size: 30px; color: #fff; background: none; border: none; cursor: pointer; }}
        
        /* Sidebar */
        .sidebar {{ width: var(--sidebar-w); background: #fff; border-right: 1px solid var(--border); display: flex; flex-direction: column; z-index: 200; box-shadow: 2px 0 5px rgba(0,0,0,0.05); transition: transform 0.3s; flex-shrink: 0; }}
        .sidebar.closed {{ transform: translateX(calc(-1 * var(--sidebar-w))); margin-right: calc(-1 * var(--sidebar-w)); }}
        .sidebar-header {{ padding: 15px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: #f1f1f1; }}
        .sidebar-content {{ flex: 1; overflow-y: auto; padding: 20px; }}
        .placeholder-text {{ color: #999; text-align: center; margin-top: 50px; font-style: italic; }}
        .sidebar-actions {{ padding: 15px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 10px; background: #f9f9f9; }}
        .btn-action {{ display: block; text-align: center; padding: 10px; border-radius: 4px; text-decoration: none; border: 1px solid var(--border); background: #fff; color: #333; }}
        .btn-action.primary {{ background: var(--primary); color: #fff; border: none; }}
        
        /* Main Layout - Don't Expand */
        .main-layout {{ 
            flex: 1; 
            display: flex; 
            flex-direction: column; 
            min-width: 0;
            max-height: 100vh;
            overflow: hidden;
        }}
        
        /* Toolbar - Fixed Height */
        .sticky-toolbar {{ 
            background: #fff; 
            border-bottom: 1px solid var(--border); 
            padding: 12px 20px; 
            z-index: 100; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            flex-shrink: 0;
        }}
        .toolbar-row {{ display: flex; flex-wrap: wrap; align-items: center; gap: 15px; margin-bottom: 10px; }} /* Added wrap */
        .toolbar-row.secondary {{ margin-bottom: 0; font-size: 13px; color: #666; justify-content: space-between; }}
        
        /* Inputs */
        .search-box {{ flex: 1; position: relative; min-width: 250px; }}
        .search-box input {{ width: 100%; padding: 8px 10px 8px 30px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }} /* box-sizing fix */
        .search-icon {{ position: absolute; left: 8px; top: 50%; transform: translateY(-50%); opacity: 0.5; }}
        
        .filter-group {{ display: flex; align-items: center; gap: 8px; font-size: 13px; white-space: nowrap; }}
        .filter-group select {{ padding: 5px; border-radius: 4px; border: 1px solid #ccc; max-width: 150px; }}
        
        /* View Toggles */
        .view-toggles {{ display: flex; border: 1px solid #ccc; border-radius: 4px; overflow: hidden; margin-left: auto; }} /* margin-left auto pushes to right */
        .btn-toggle {{ border: none; background: #f0f0f0; padding: 8px 14px; cursor: pointer; border-right: 1px solid #ccc; font-size: 13px; }}
        .btn-toggle:last-child {{ border-right: none; }}
        .btn-toggle.active {{ background: var(--primary); color: #fff; }}

        /* Content Area - Fixed Height Viewport */
        .content-area {{ 
            height: calc((var(--grid-size) * 4) + (20px * 3) + 40px);
            overflow-y: scroll; 
            overflow-x: hidden;
            padding: 20px; 
            background: #fafafa;
            flex-shrink: 0;
            flex-grow: 0;
        }}
        
        /* Wide Scrollbar with Textured Track */
        .content-area::-webkit-scrollbar {{
            width: 20px;
        }}
        
        .content-area::-webkit-scrollbar-track {{
            background: 
                repeating-linear-gradient(
                    45deg,
                    #e0e0e0,
                    #e0e0e0 2px,
                    #ececec 2px,
                    #ececec 4px
                );
            border-left: 1px solid #b8b8b8;
            border-right: 1px solid #ffffff;
            box-shadow: inset 1px 0 2px rgba(0,0,0,0.1);
        }}
        
        .content-area::-webkit-scrollbar-thumb {{
            background: linear-gradient(to right, 
                #c8c8c8 0%, 
                #e8e8e8 20%,
                #f4f4f4 50%, 
                #e8e8e8 80%,
                #c8c8c8 100%
            );
            border: 1px solid #989898;
            border-radius: 3px;
            box-shadow: 
                inset 0 0 0 1px rgba(255,255,255,0.6),
                0 1px 3px rgba(0,0,0,0.15);
        }}
        
        .content-area::-webkit-scrollbar-thumb:hover {{
            background: linear-gradient(to right, 
                #b8b8b8 0%, 
                #d8d8d8 20%,
                #e4e4e4 50%, 
                #d8d8d8 80%,
                #b8b8b8 100%
            );
        }}
        
        .content-area::-webkit-scrollbar-thumb:active {{
            background: linear-gradient(to right, 
                #a8a8a8 0%, 
                #c8c8c8 20%,
                #d4d4d4 50%, 
                #c8c8c8 80%,
                #a8a8a8 100%
            );
        }}
        
        /* Grid View - Image-First Design */
        .view-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(var(--grid-size), 1fr)); gap: 20px; align-content: start; }}
        .card {{ 
            background: #fff; 
            border: 1px solid #eee; 
            border-radius: 8px; 
            overflow: hidden; 
            transition: 0.2s; 
            cursor: pointer; 
            display: flex; 
            flex-direction: column;
            height: var(--grid-size);
            position: relative;
        }}
        .card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 16px rgba(0,0,0,0.15); }}
        .card.selected {{ border-color: var(--primary); box-shadow: 0 0 0 3px rgba(0,123,255,0.2); }}
        
        /* Card Thumbnail - Full Card Background */
        .card-thumb {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #eee;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .thumb-fallback {{
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            display: flex; align-items: center; justify-content: center;
            z-index: 1;
            font-size: calc(var(--grid-size) * 0.4);
            color: #ccc;
        }}

        .card-thumb img {{
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            object-fit: cover;
            display: block;
            z-index: 2;
        }}
        
        /* No preview icon for non-images */
        .no-preview {{ 
            font-weight: bold; 
            color: #bbb; 
            letter-spacing: 1px; 
            font-size: calc(var(--grid-size) * 0.4); 
            z-index: 3;
        }}
        
        /* Card Body - Overlaid on Image */
        .card-body {{ 
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 8px 10px;
            background: linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.5) 70%, transparent 100%);
            z-index: 10;
            pointer-events: none;
        }}
        
        .card-title {{ 
            font-size: 12px; 
            font-weight: 500; 
            color: #fff;
            text-shadow: 0 1px 3px rgba(0,0,0,0.8);
            margin-bottom: 2px; 
            word-break: break-word; 
            line-height: 1.2; 
            max-height: 2.4em; 
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }}
        
        .card-meta {{ 
            font-size: 10px; 
            color: rgba(255,255,255,0.9);
            text-shadow: 0 1px 2px rgba(0,0,0,0.6);
        }}

        /* List/Compact Views */
        .view-list .list-row {{ padding: 12px; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; }}
        .list-icon {{ width: 48px; height: 48px; border-radius: 6px; margin-right: 15px; flex-shrink: 0; background: #eee; display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative; }}
        .list-icon img {{ width: 100%; height: 100%; object-fit: cover; display: block; position: absolute; top: 0; left: 0; z-index: 2; background: #fff; }}
        .list-icon .thumb-fallback {{ font-size: 24px; position: absolute; top:0; left:0; width:100%; height:100%; z-index: 1; }}
        .list-icon .no-preview {{ font-size: 24px; }}
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
        pageSize: 50, // Reduced from 100 for better initial performance
        selectedId: null,
        renderBatchSize: 20, // Render 20 items at a time for progressive rendering
        isRendering: false,

        init: function() {{
            this.data = window.fileData.map((d, i) => ({{...d, id: i}}));
            this.populateTypes();
            this.applyFilters();
            // Explicitly set grid-size to ensure it's applied
            const zoomValue = document.getElementById('zoomSlider').value;
            document.documentElement.style.setProperty('--grid-size', zoomValue + 'px');
        }},
        
        updateZoom: function(val) {{
            document.documentElement.style.setProperty('--grid-size', val + "px");
        }},
        
        populateTypes: function() {{
            const types = new Set(this.data.map(d => d.ext));
            const sel = document.getElementById('typeFilter');
            sel.innerHTML = '<option value="all">All Types</option>';
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
            // Toggle Zoom visibility
            document.getElementById('zoomControl').style.display = (v === 'grid') ? 'flex' : 'none';
            this.render();
        }},

        setSort: function(field) {{
            if (this.sort === field + '_asc') {{
                this.sort = field + '_desc';
            }} else if (this.sort === field + '_desc') {{
               this.sort = field + '_asc';
            }} else {{
               this.sort = field + '_asc';
            }}
            
            // Special handling for 'name' which user simplified to just 'name'
            if (field === 'name') {{
                if (this.sort === 'name') this.sort = 'name_desc';
                else this.sort = 'name';
            }}
            
            document.getElementById('sortField').value = this.sort; 
            this.page = 1;
            this.sortData();
            this.render();
        }},

        openLightbox: function(src) {{
            if (typeof src !== 'string' || !src.startsWith('file')) return; 
            const lb = document.getElementById('lightbox');
            document.getElementById('lightboxImg').src = src;
            lb.classList.add('active');
        }},
        
        closeLightbox: function() {{
            document.getElementById('lightbox').classList.remove('active');
        }},

        applyFilters: function() {{
            const now = Date.now() / 1000;
            this.filtered = this.data.filter(item => {{
                if (item.category === 'disk_image' && !this.filters.disk) return false;
                if (item.category === 'media_file' && !this.filters.media) return false;
                if (this.search && !item.name.toLowerCase().includes(this.search)) return false;
                if (this.filters.type !== 'all' && item.ext !== this.filters.type) return false;
                
                const s = item.size;
                if (this.filters.size === 'small' && s >= 1048576) return false;
                if (this.filters.size === 'medium' && (s < 1048576 || s >= 104857600)) return false;
                if (this.filters.size === 'large'  && (s < 104857600 || s >= 1073741824)) return false;
                if (this.filters.size === 'huge'   && s < 1073741824) return false;

                if (this.filters.date !== 'all') {{
                    const age = (now - item.mtime) / 86400;
                    if (this.filters.date === 'today' && age > 1) return false;
                    if (this.filters.date === 'week' && age > 7) return false;
                    if (this.filters.date === 'month' && age > 30) return false;
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
                if (s === 'name_asc') return a.name.localeCompare(b.name);
                if (s === 'name_desc') return b.name.localeCompare(a.name);
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
            this.render(); 
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
            
            if (icon.type === 'img') {{
                thumbInfo = `<img src="${{icon.src}}" 
                    style="max-width:100%; border-radius:4px; margin-bottom:15px; box-shadow:0 2px 5px rgba(0,0,0,0.1); cursor:zoom-in;" 
                    onclick="app.openLightbox('${{icon.src}}')">`;
            }} else {{
                thumbInfo = `<div style="font-size:3em; color:#ccc; text-align:center; padding:20px;">${{icon.val}}</div>`;
            }}

            content.innerHTML = `
                ${{thumbInfo}}
                <div style="font-weight:bold; word-break:break-all; font-size:1.1em;">${{item.name}}</div>
                <div style="font-size:0.9em; color:#666; margin:5px 0 15px;">${{item.formatted_size}} • ${{item.ext}}</div>
                
                <div style="font-size:0.85em; display:grid; grid-template-columns:auto 1fr; gap:5px 10px;">
                    <strong>Path:</strong> <span style="word-break:break-all;">${{item.path}}</span>
                    <strong>Date:</strong> <span>${{item.formatted_date}}</span>
                    <strong>Type:</strong> <span>${{item.category}}</span>
                </div>
            `;
            
            document.getElementById('btnOpen').href = item.file_url;
            document.getElementById('btnReveal').href = item.file_url; 
        }},
        
        getIcon: function(item) {{
             const ext = item.ext.toLowerCase();
             
             // UNIFIED LOGIC: If a generated thumbnail exists, USE IT.
             if (item.thumb_url) {{
                 return {{type:'img', src: item.thumb_url}};
             }}

             // Safe web images fallback to absolute path
             if (['.jpg','.jpeg','.png','.gif','.webp','.svg'].includes(ext)) {{
                 return {{type:'img', src: item.file_url}};
             }}
             // Disk Images -> CD Icon
             if (['.dmg','.iso','.img','.dd','.cdr','.vmdk'].includes(ext)) {{
                 return {{type:'text', val: '💿'}};
             }}
             // Non-Web Visual Media -> Picture Frame
             if (['.tiff','.tif','.psd','.ai','.eps','.bmp','.heic'].includes(ext)) {{
                 return {{type:'text', val: '🖼️'}};
             }}
             // Archives
             if (['.zip','.tar','.gz','.7z'].includes(ext)) {{
                 return {{type:'text', val: '📦'}};
             }}
             return {{type:'text', val: '📄'}};
        }},

        render: function() {{
            if (this.isRendering) return; // Prevent concurrent renders
            this.isRendering = true;
            
            const container = document.getElementById('contentArea');
            container.innerHTML = '';
            
            const start = (this.page - 1) * this.pageSize;
            const pageData = this.filtered.slice(start, start + this.pageSize);
            
            const maxPage = Math.ceil(this.filtered.length / this.pageSize) || 1;
            document.getElementById('pageInfo').textContent = `Page ${{this.page}} of ${{maxPage}}`;
            document.getElementById('statusBar').textContent = `Found ${{this.filtered.length}} items (Total: ${{this.data.length}})`;
            document.getElementById('btnPrev').disabled = (this.page === 1);
            document.getElementById('btnNext').disabled = (this.page === maxPage);

            // Show loading indicator for large datasets
            if (pageData.length > this.renderBatchSize) {{
                container.innerHTML = '<div style="text-align:center; padding:40px; color:#666;">Rendering ${{pageData.length}} items...</div>';
            }}

            // Special handling for table view - create table structure first
            if (this.view === 'compact') {{
                const table = document.createElement('table');
                table.className = 'compact-table';
                table.innerHTML = `<thead><tr>
                    <th onclick="app.setSort('name')" style="cursor:pointer">Name</th>
                    <th onclick="app.setSort('size')" style="cursor:pointer">Size</th>
                    <th onclick="app.setSort('date')" style="cursor:pointer">Date</th>
                    <th>Path</th>
                </tr></thead>`;
                const tbody = document.createElement('tbody');
                table.appendChild(tbody);
                container.innerHTML = '';
                container.appendChild(table);
            }}

            // Progressive rendering for better performance
            let currentIndex = 0;
            const self = this;
            
            function renderBatch() {{
                const batchEnd = Math.min(currentIndex + self.renderBatchSize, pageData.length);
                const fragment = document.createDocumentFragment();
                
                for (let i = currentIndex; i < batchEnd; i++) {{
                    const item = pageData[i];
                    const element = self.createItemElement(item);
                    if (element) {{
                        fragment.appendChild(element);
                    }}
                }}
                
                // Append to appropriate container
                if (self.view === 'compact') {{
                    const tbody = container.querySelector('tbody');
                    tbody.appendChild(fragment);
                }} else {{
                    // Clear loading message on first batch for grid/list views
                    if (currentIndex === 0) {{
                        container.innerHTML = '';
                    }}
                    container.appendChild(fragment);
                }}
                
                currentIndex = batchEnd;
                
                // Continue rendering if there are more items
                if (currentIndex < pageData.length) {{
                    requestAnimationFrame(renderBatch);
                }} else {{
                    self.isRendering = false;
                }}
            }}
            
            // Start progressive rendering
            requestAnimationFrame(renderBatch);
        }},
        
        createItemElement: function(item) {{
            const sel = item.id === this.selectedId ? 'selected' : '';
            const icon = this.getIcon(item);
            
            if (this.view === 'compact') {{
                const tr = document.createElement('tr');
                tr.className = sel;
                if (item.dup_group) tr.style.background = '#fff3cd';
                tr.onclick = () => this.selectItem(item.id);
                tr.innerHTML = `
                    <td>${{item.name}}</td>
                    <td>${{item.formatted_size}}</td>
                    <td>${{item.formatted_date}}</td>
                    <td title="${{item.path}}">
                        <div style="max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                            ${{item.path}}
                        </div>
                    </td>`;
                return tr;
            }} else {{
                let thumb = '';
                if (icon.type === 'img') {{
                    thumb = `
                        <div class="thumb-fallback">🖼️</div>
                        <img src="${{icon.src}}" loading="lazy" onerror="this.style.display='none'">
                    `;
                }} else {{
                    thumb = `<div class="no-preview">${{icon.val}}</div>`;
                }}
                
                const div = document.createElement('div');
                div.onclick = () => this.selectItem(item.id);
                
                if (this.view === 'grid') {{
                    div.className = `card ${{sel}}`;
                    div.innerHTML = `
                        <div class="card-thumb">${{thumb}}</div>
                        <div class="card-body">
                            <div class="card-title" title="${{item.name}}">${{item.name}}</div>
                            <div class="card-meta">${{item.formatted_size}}</div>
                        </div>`;
                }} else {{
                    div.className = `list-row ${{sel}}`;
                    div.innerHTML = `
                        <div class="list-icon">${{thumb}}</div>
                        <div style="flex:1; min-width:0;">
                            <div style="font-weight:500; margin-bottom:2px;">${{item.name}}</div>
                            <div style="font-size:11px; color:#888; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                                ${{item.path}}
                            </div>
                        </div>
                        <div style="flex-shrink:0; width:100px; text-align:right; font-size:12px; color:#666;">
                            ${{item.formatted_size}}
                        </div>`;
                }}
                
                return div;
            }}
        }}
    }};
    
    document.addEventListener('DOMContentLoaded', () => APP.init());
    window.app = APP;
    </script>
    """


def render_report(
    app_instance: Any,
    helpers: Helpers,
    json_data: str,
    # html_body argument removed as we generate it here
    browser_preference: str,
) -> None:
    # Generate the body here using the JSON data
    html_body = get_html_body(json_data)
    
    helpers.generate_report_html(
        app_instance,
        app_instance.suspect_computer_name,
        "Images_Report.html",
        "Advanced Disk & Media Artifacts",
        html_body,
        browser_preference=browser_preference,
    )
