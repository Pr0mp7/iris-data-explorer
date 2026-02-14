/* IRIS Data Explorer — Main application logic */

document.addEventListener('DOMContentLoaded', function () {
    // ── Theme toggle ────────────────────────────────────────────
    var themeBtn = document.getElementById('theme-toggle');
    var themeIcon = document.getElementById('theme-icon');

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        if (themeIcon) themeIcon.textContent = theme === 'dark' ? '\u2600' : '\u263E';
    }

    if (themeBtn) {
        var saved = localStorage.getItem('ide-theme') || 'dark';
        applyTheme(saved);

        themeBtn.addEventListener('click', function () {
            var current = document.documentElement.getAttribute('data-bs-theme');
            var next = current === 'dark' ? 'light' : 'dark';
            applyTheme(next);
            localStorage.setItem('ide-theme', next);
        });
    }

    // ── Helpers ──────────────────────────────────────────────────

    function escapeHtml(s) {
        if (s === null || s === undefined) return '';
        var div = document.createElement('div');
        div.textContent = String(s);
        return div.innerHTML;
    }

    function stripHtml(s) {
        if (!s) return '';
        return String(s).replace(/<[^>]+>|<!--.*?-->/gs, '').trim();
    }

    function truncate(s, len) {
        if (!s) return '';
        s = String(s);
        return s.length > len ? s.substring(0, len) + '...' : s;
    }

    function val(obj, keys) {
        for (var i = 0; i < keys.length; i++) {
            var v = obj[keys[i]];
            if (v !== undefined && v !== null) return v;
        }
        return '';
    }

    // Read config from data attributes (CSP-safe, no inline scripts)
    var _body = document.body;
    var CASE_ID = _body.dataset.caseId ? parseInt(_body.dataset.caseId, 10) : undefined;
    var IRIS_URL = _body.dataset.irisUrl || '';
    var REFRESH_INTERVAL = _body.dataset.refreshInterval ? parseInt(_body.dataset.refreshInterval, 10) : 0;

    function irisLink(path, text) {
        if (!IRIS_URL) return escapeHtml(text);
        return '<a href="' + escapeHtml(IRIS_URL) + path + '" target="_blank" ' +
               'class="text-decoration-none">' + escapeHtml(text) + '</a>';
    }

    // ── IRIS lookup cache (#4 — resolve IDs to human labels) ────
    var lookupCache = {};

    function fetchLookups() {
        $.getJSON('/api/lookups', function (data) {
            lookupCache = data || {};
            // Re-draw all tables to apply labels
            Object.keys(tables).forEach(function (key) {
                if (tables[key]) tables[key].rows().invalidate().draw(false);
            });
            // #16: Populate header status/severity badges
            var hStatus = document.getElementById('header-status-badge');
            if (hStatus && hStatus.dataset.statusId) {
                var sLabel = resolveLookup('case_status', hStatus.dataset.statusId);
                hStatus.textContent = sLabel;
                var sLower = String(sLabel).toLowerCase();
                hStatus.className = 'badge-status badge ms-2 ' +
                    (sLower.indexOf('open') !== -1 ? 'bg-info' :
                     sLower.indexOf('clos') !== -1 ? 'bg-success' : 'bg-secondary');
            }
            var hSeverity = document.getElementById('header-severity-badge');
            if (hSeverity && hSeverity.dataset.severityId) {
                var sevLabel = resolveLookup('severity', hSeverity.dataset.severityId);
                hSeverity.textContent = sevLabel;
                var sevLower = String(sevLabel).toLowerCase();
                hSeverity.className = 'badge-severity badge ms-1 ' +
                    (sevLower.indexOf('critical') !== -1 || sevLower.indexOf('high') !== -1 ? 'bg-danger' :
                     sevLower.indexOf('medium') !== -1 || sevLower.indexOf('med') !== -1 ? 'bg-warning text-dark' :
                     sevLower.indexOf('low') !== -1 ? 'bg-info' : 'bg-secondary');
            }
        });
    }

    function resolveLookup(type, id) {
        if (id === null || id === undefined || id === '') return '';
        var map = lookupCache[type];
        if (map && map[String(id)]) return map[String(id)];
        return String(id);
    }

    // TLP color map (#10)
    var TLP_COLORS = {
        'TLP:RED': { bg: '#cc0000', text: '#ffffff' },
        'TLP:AMBER': { bg: '#ff8c00', text: '#1a1a1a' },
        'TLP:AMBER+STRICT': { bg: '#ff8c00', text: '#1a1a1a' },
        'TLP:GREEN': { bg: '#33a532', text: '#ffffff' },
        'TLP:CLEAR': { bg: '#ffffff', text: '#1a1a1a', border: '#ccc' },
        'TLP:WHITE': { bg: '#ffffff', text: '#1a1a1a', border: '#ccc' }
    };

    function tlpBadge(id) {
        var label = resolveLookup('tlp', id);
        if (!label) return '';
        var upper = String(label).toUpperCase();
        // Try exact match, then prefix match
        var color = TLP_COLORS[upper];
        if (!color) {
            for (var key in TLP_COLORS) {
                if (upper.indexOf(key.replace('TLP:', '')) !== -1) {
                    color = TLP_COLORS[key];
                    break;
                }
            }
        }
        if (color) {
            var style = 'background:' + color.bg + ';color:' + color.text;
            if (color.border) style += ';border:1px solid ' + color.border;
            return '<span class="badge" style="' + style + '">' + escapeHtml(label) + '</span>';
        }
        return '<span class="badge bg-secondary">' + escapeHtml(label) + '</span>';
    }

    // Status badge (#16)
    function statusBadge(id) {
        var label = resolveLookup('case_status', id);
        if (!label) return escapeHtml(id);
        var lower = String(label).toLowerCase();
        var cls = 'bg-secondary';
        if (lower.indexOf('open') !== -1) cls = 'bg-info';
        else if (lower.indexOf('closed') !== -1 || lower.indexOf('close') !== -1) cls = 'bg-success';
        return '<span class="badge ' + cls + '">' + escapeHtml(label) + '</span>';
    }

    // Severity badge (#16)
    function severityBadge(id) {
        var label = resolveLookup('severity', id);
        if (!label) return escapeHtml(id);
        var lower = String(label).toLowerCase();
        var cls = 'bg-secondary';
        if (lower.indexOf('critical') !== -1) cls = 'bg-danger';
        else if (lower.indexOf('high') !== -1) cls = 'bg-danger';
        else if (lower.indexOf('medium') !== -1 || lower.indexOf('med') !== -1) cls = 'bg-warning text-dark';
        else if (lower.indexOf('low') !== -1) cls = 'bg-info';
        return '<span class="badge ' + cls + '">' + escapeHtml(label) + '</span>';
    }

    // ── Column filters ───────────────────────────────────────────
    function addColumnFilters(dt) {
        var headerRow = $(dt.table().header()).find('tr').first();
        // Prevent duplicate filter rows
        if ($(dt.table().header()).find('.dt-column-filters').length > 0) return;
        var filterRow = $('<tr class="dt-column-filters"></tr>');

        dt.columns().every(function (idx) {
            var col = this;
            var th = $(headerRow.find('th').eq(idx));
            var td = $('<th></th>');

            // Skip non-searchable columns (like "Details" / action buttons)
            if (col.dataSrc() === 'raw_data' || th.text() === 'Actions' || th.text() === '' || th.text() === 'Details') {
                filterRow.append(td);
                return;
            }

            var input = $('<input type="text" class="form-control form-control-sm col-filter-input" placeholder="' + th.text() + '...">')
            td.append(input);
            filterRow.append(td);

            // Debounce search to avoid too many redraws
            var timer;
            input.on('keyup change clear', function () {
                var val = this.value;
                clearTimeout(timer);
                timer = setTimeout(function () {
                    if (col.search() !== val) {
                        col.search(val).draw();
                    }
                }, 300);
            });

            // Prevent sorting when clicking on the filter input
            input.on('click', function (e) { e.stopPropagation(); });
        });

        headerRow.after(filterRow);
    }

    function copyBtn(text) {
        if (!text) return '';
        var escaped = escapeHtml(String(text));
        return escaped + ' <button class="btn btn-link btn-sm p-0 ms-1 copy-btn" ' +
               'data-copy="' + escaped + '" title="Copy">' +
               '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">' +
               '<path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 010 1.5h-1.5a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-1.5a.75.75 0 011.5 0v1.5A1.75 1.75 0 019.25 16h-7.5A1.75 1.75 0 010 14.25z"/>' +
               '<path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0114.25 11h-7.5A1.75 1.75 0 015 9.25zm1.75-.25a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-7.5a.25.25 0 00-.25-.25z"/>' +
               '</svg></button>';
    }

    // ── Copy to clipboard handler ───────────────────────────────
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.copy-btn');
        if (!btn) return;
        e.preventDefault();
        var text = btn.getAttribute('data-copy');
        navigator.clipboard.writeText(text).then(function () {
            btn.title = 'Copied!';
            setTimeout(function () { btn.title = 'Copy'; }, 1500);
        });
    });

    // ── Copy row as JSON handler (#20) ──────────────────────────
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.copy-json-btn');
        if (!btn) return;
        e.preventDefault();
        var json = decodeURIComponent(escape(atob(btn.getAttribute('data-row-b64'))));
        navigator.clipboard.writeText(json).then(function () {
            btn.title = 'Copied!';
            btn.classList.add('text-success');
            setTimeout(function () { btn.title = 'Copy as JSON'; btn.classList.remove('text-success'); }, 1500);
        });
    });

    // ── Auto-refresh status ─────────────────────────────────────
    var refreshInterval = REFRESH_INTERVAL || 0;
    var statusEl = document.getElementById('refresh-status');
    var lastRefresh = new Date();

    function updateStatus() {
        if (!statusEl || !refreshInterval) return;
        var ago = Math.round((new Date() - lastRefresh) / 1000);
        var next = Math.max(0, refreshInterval - ago);
        statusEl.textContent = 'Updated ' + ago + 's ago | Next in ' + next + 's';
    }

    if (statusEl && refreshInterval) {
        setInterval(updateStatus, 1000);
        updateStatus();
    }

    // ── Refresh helpers: preserve expanded rows + subtle spinner ──
    var refreshBtn = document.getElementById('btn-refresh');

    // Map entity key → row ID field name
    var entityIdField = {
        assets: 'asset_id', iocs: 'ioc_id', events: 'event_id',
        tasks: 'task_id', notes: 'note_id', evidences: 'evidence_id',
        shadowserver: 'report_date'
    };

    function getExpandedRowIds(dt, entity) {
        var ids = [];
        var idField = entityIdField[entity];
        dt.rows().every(function () {
            if (this.child.isShown()) {
                var d = this.data();
                var val = idField ? d[idField] : d[Object.keys(d)[0]];
                if (val != null) ids.push(String(val));
            }
        });
        return ids;
    }

    function restoreExpandedRows(dt, ids, entity) {
        if (!ids.length) return;
        var idField = entityIdField[entity];
        dt.rows().every(function () {
            var d = this.data();
            var val = idField ? d[idField] : d[Object.keys(d)[0]];
            if (val != null && ids.indexOf(String(val)) !== -1) {
                var tr = this.node();
                if (!tr) return;
                var b64 = tr.getAttribute('data-row-json');
                if (!b64) return;
                var data;
                try { data = JSON.parse(decodeURIComponent(escape(atob(b64)))); } catch (ex) { return; }
                this.child(buildRowDetail(b64, data)).show();
                $(tr).addClass('row-expanded');
            }
        });
    }

    function startRefreshSpin() {
        if (refreshBtn) {
            refreshBtn.innerHTML = '<span class="refresh-spinner"></span>';
            refreshBtn.disabled = true;
        }
    }

    function stopRefreshSpin() {
        if (refreshBtn) {
            refreshBtn.innerHTML = '&#8635;';
            refreshBtn.disabled = false;
        }
    }

    function refreshAllTables(bustCache) {
        var suffix = bustCache ? '?refresh=1' : '';
        var pending = 0;
        var expandedState = {};

        // Save expanded rows for each initialized table
        Object.keys(tables).forEach(function (key) {
            if (tables[key]) {
                expandedState[key] = getExpandedRowIds(tables[key], key);
                pending++;
            }
        });

        if (!pending) return;
        startRefreshSpin();

        Object.keys(tables).forEach(function (key) {
            var t = tables[key];
            if (!t) return;
            var url = key === 'shadowserver'
                ? '/api/dt/case/' + CASE_ID + '/shadowserver' + suffix
                : '/api/dt/case/' + CASE_ID + '/' + key + suffix;
            t.ajax.url(url).load(function () {
                if (expandedState[key] && expandedState[key].length) {
                    restoreExpandedRows(t, expandedState[key], key);
                }
                pending--;
                if (pending <= 0) {
                    lastRefresh = new Date();
                    stopRefreshSpin();
                }
            }, false);
        });
    }

    // Manual refresh button
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function () {
            refreshAllTables(true);
        });
    }

    // Cases list manual refresh
    var refreshCasesBtn = document.getElementById('btn-refresh-cases');

    // ── Cases list page (AJAX DataTable) ────────────────────────
    var casesTable = document.getElementById('cases-table');
    if (casesTable && CASE_ID === undefined) {
        var irisUrl = (typeof IRIS_URL !== 'undefined') ? IRIS_URL : '';
        var dt = new DataTable('#cases-table', {
            serverSide: true,
            processing: true,
            pageLength: 25,
            lengthMenu: [[10, 25, 50, 100], [10, 25, 50, 100]],
            dom: 'lBfrtip',
            stateSave: true,
            buttons: ['csv'],
            autoWidth: false,
            order: [[0, 'desc']],
            initComplete: function () { addColumnFilters(this.api()); },
            ajax: {
                url: '/api/dt/cases',
                dataSrc: 'data'
            },
            columns: [
                { data: 'case_id', width: '40px' },
                { data: 'case_name', width: '22%', render: function (d) { return '<span title="' + escapeHtml(d) + '">' + escapeHtml(truncate(d, 50)) + '</span>'; } },
                { data: 'case_description', width: '20%', render: function (d) { return escapeHtml(truncate(stripHtml(d), 60)); } },
                { data: 'case_soc_id', width: '70px', defaultContent: '' },
                { data: 'status_id', width: '70px', defaultContent: '', render: function (d) {
                    return d != null ? statusBadge(d) : '';
                }},
                { data: 'severity_id', width: '75px', defaultContent: '', render: function (d) {
                    return d != null ? severityBadge(d) : '';
                }},
                { data: 'owner', width: '90px', defaultContent: '', render: function (d) {
                    if (!d) return '';
                    var name = d.user_name || d.user_login || d;
                    return '<span title="' + escapeHtml(name) + '">' + escapeHtml(truncate(name, 12)) + '</span>';
                }},
                { data: 'open_date', width: '85px', defaultContent: '' },
                { data: 'close_date', width: '85px', defaultContent: '' },
                { data: 'case_id', width: '110px', orderable: false, render: function (d) {
                    return '<a href="/case/' + d + '" class="btn btn-sm btn-primary py-0 px-2">Explore</a> ' +
                           '<a href="' + escapeHtml(irisUrl) + '/case?cid=' + d + '" target="_blank" ' +
                           'class="btn btn-sm btn-outline-info py-0 px-2" title="Open in IRIS">IRIS</a>';
                }}
            ],
            language: {
                emptyTable: 'No cases found',
                search: 'Filter:',
                processing: '<div class="spinner-border spinner-border-sm" role="status"></div> Loading...'
            }
        });

        // Fetch lookups for label resolution
        fetchLookups();

        // Cases list manual refresh
        if (refreshCasesBtn) {
            refreshCasesBtn.addEventListener('click', function () {
                refreshCasesBtn.disabled = true;
                refreshCasesBtn.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div>';
                dt.ajax.url('/api/dt/cases?refresh=1').load(function () {
                    lastRefresh = new Date();
                    refreshCasesBtn.disabled = false;
                    refreshCasesBtn.innerHTML = '&#8635;';
                }, false);
            });
        }

        // Auto-refresh cases table
        if (refreshInterval > 0) {
            setInterval(function () {
                dt.ajax.url('/api/dt/cases?refresh=1').load(null, false);
                lastRefresh = new Date();
            }, refreshInterval * 1000);
        }
        return;
    }

    // ── Server-side DataTables (case explorer) ──────────────────
    if (CASE_ID === undefined) return;

    // Fetch lookups for label resolution
    fetchLookups();

    var dtDefaults = {
        serverSide: true,
        processing: false,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100], [10, 25, 50, 100]],
        dom: 'lBfrtip',
        stateSave: true,
        buttons: ['csv', 'copy'],
        autoWidth: false,
        language: {
            emptyTable: 'No data available',
            search: 'Filter:'
        },
        initComplete: function () {
            addColumnFilters(this.api());
        }
    };

    var tables = {};

    // ── Deferred tab loading (#19) ──────────────────────────────
    // Only initialize the active tab's table immediately.
    // Other tabs are initialized when first clicked.
    var pendingInits = {};

    function initTable(selector, entity, columns) {
        return new DataTable(selector, $.extend(true, {}, dtDefaults, {
            ajax: {
                url: '/api/dt/case/' + CASE_ID + '/' + entity,
                dataSrc: 'data'
            },
            columns: columns,
            order: [[0, 'desc']],
            // #3: row expand — child row on click
            createdRow: function (row, data) {
                $(row).addClass('expandable-row');
                $(row).attr('data-row-json', btoa(unescape(encodeURIComponent(JSON.stringify(data, null, 2)))));
            },
            drawCallback: function (settings) {
                // #1: Update entity count badge
                var info = this.api().page.info();
                updateTabBadge(entity, info.recordsTotal);
            }
        }));
    }

    function registerDeferred(entity, selector, columns) {
        pendingInits[entity] = { selector: selector, columns: columns };
    }

    function initDeferred(entity) {
        if (pendingInits[entity]) {
            var cfg = pendingInits[entity];
            tables[entity] = initTable(cfg.selector, entity, cfg.columns);
            delete pendingInits[entity];
        }
    }

    // #1: Entity count badge updater
    function updateTabBadge(entity, count) {
        var badge = document.getElementById('badge-' + entity);
        if (badge) {
            badge.textContent = count != null ? count.toLocaleString() : '0';
            badge.style.display = (count != null && count > 0) ? 'inline' : 'none';
        }
    }

    // Column definitions for each entity
    var entityColumns = {
        assets: [
            { data: 'asset_id', render: function (d, t, r) {
                return irisLink('/case/assets/' + d + '?cid=' + CASE_ID, d);
            }},
            { data: 'asset_name', render: function (d) { return escapeHtml(d); } },
            { data: 'asset_ip', render: function (d) { return copyBtn(d); } },
            { data: 'asset_domain', render: function (d) { return copyBtn(d); } },
            { data: 'asset_type_id', render: function (d) { return escapeHtml(resolveLookup('asset_type', d)); } },
            { data: 'asset_compromise_status_id', render: function (d) { return escapeHtml(resolveLookup('compromise_status', d)); } },
            { data: 'asset_description', render: function (d) { return escapeHtml(truncate(stripHtml(d), 200)); } },
            { data: 'date_added' }
        ],
        iocs: [
            { data: 'ioc_id', render: function (d, t, r) {
                return irisLink('/case/ioc/' + d + '?cid=' + CASE_ID, d);
            }},
            { data: 'ioc_value', render: function (d) { return copyBtn(d); } },
            { data: 'ioc_type_id', render: function (d) { return escapeHtml(resolveLookup('ioc_type', d)); } },
            { data: 'ioc_tlp_id', render: function (d) { return tlpBadge(d); } },
            { data: 'ioc_tags', render: function (d) { return escapeHtml(d); } },
            { data: 'ioc_description', render: function (d) { return escapeHtml(truncate(stripHtml(d), 200)); } }
        ],
        events: [
            { data: 'event_id', render: function (d, t, r) {
                return irisLink('/case/timeline/' + d + '?cid=' + CASE_ID, d);
            }},
            { data: 'event_date' },
            { data: 'event_title', render: function (d) { return escapeHtml(d); } },
            { data: 'event_source', render: function (d) { return escapeHtml(d); } },
            { data: 'event_tags', render: function (d) { return escapeHtml(d); } },
            { data: 'event_content', render: function (d) { return escapeHtml(truncate(stripHtml(d), 200)); } }
        ],
        tasks: [
            { data: 'task_id', defaultContent: '', render: function (d, t, r) {
                var id = d || val(r, ['id']);
                return irisLink('/case/task/' + id + '?cid=' + CASE_ID, id);
            }},
            { data: 'task_title', defaultContent: '', render: function (d) { return escapeHtml(d); } },
            { data: 'task_status_id', defaultContent: '', render: function (d) { return escapeHtml(resolveLookup('task_status', d)); } },
            { data: 'task_tags', defaultContent: '', render: function (d) { return escapeHtml(d); } },
            { data: 'task_open_date', defaultContent: '' },
            { data: 'task_close_date', defaultContent: '' },
            { data: 'task_description', defaultContent: '', render: function (d) { return escapeHtml(truncate(stripHtml(d), 200)); } }
        ],
        notes: [
            { data: 'note_id', defaultContent: '', render: function (d, t, r) {
                var id = d || val(r, ['id']);
                return irisLink('/case/notes/' + id + '?cid=' + CASE_ID, id);
            }},
            { data: 'note_title', defaultContent: '', render: function (d, t, r) {
                return escapeHtml(d || val(r, ['title']) || '');
            }},
            { data: 'note_directory', defaultContent: '' },
            { data: 'note_creationdate', defaultContent: '' },
            { data: 'note_lastupdate', defaultContent: '' }
        ],
        evidences: [
            { data: 'evidence_id', defaultContent: '', render: function (d, t, r) {
                var id = d || val(r, ['id']);
                return irisLink('/case/evidences/' + id + '?cid=' + CASE_ID, id);
            }},
            { data: 'filename', defaultContent: '', render: function (d) { return escapeHtml(d); } },
            { data: 'file_hash', defaultContent: '', render: function (d) { return copyBtn(d); } },
            { data: 'file_size', defaultContent: '' },
            { data: 'date_added', defaultContent: '' },
            { data: 'file_description', defaultContent: '', render: function (d) { return escapeHtml(truncate(stripHtml(d), 200)); } }
        ]
    };

    // Initialize only the active (first) tab immediately; defer the rest
    tables.assets = initTable('#dt-assets', 'assets', entityColumns.assets);
    registerDeferred('iocs', '#dt-iocs', entityColumns.iocs);
    registerDeferred('events', '#dt-events', entityColumns.events);
    registerDeferred('tasks', '#dt-tasks', entityColumns.tasks);
    registerDeferred('notes', '#dt-notes', entityColumns.notes);
    registerDeferred('evidences', '#dt-evidences', entityColumns.evidences);

    // #1: Fetch all entity counts upfront so badges show immediately
    $.getJSON('/api/case/' + CASE_ID + '/counts', function (counts) {
        for (var entity in counts) {
            updateTabBadge(entity, counts[entity]);
        }
    });

    // ── Shadowserver tab (dynamic correlation) ─────────────────
    var ssTable = document.getElementById('dt-shadowserver');
    var ssInitialized = false;

    function initShadowserver() {
        if (ssInitialized || !ssTable) return;
        ssInitialized = true;

        var ssColMap = {
            0: 'report_date', 1: 'report_type', 2: 'ip', 3: 'port',
            4: 'asn', 5: 'geo', 6: 'hostname', 7: 'tag', 8: 'severity',
        };

        tables.shadowserver = new DataTable('#dt-shadowserver', $.extend(true, {}, dtDefaults, {
            ajax: {
                url: '/api/dt/case/' + CASE_ID + '/shadowserver',
                dataSrc: 'data',
                data: function (d) {
                    if (d.order && d.order.length > 0) {
                        d.order_column = ssColMap[d.order[0].column] || 'report_date';
                        d.order_dir = d.order[0].dir || 'desc';
                    }
                }
            },
            columns: [
                { data: 'report_date' },
                { data: 'report_type', render: function (d) { return '<span class="badge bg-warning text-dark">' + escapeHtml(d) + '</span>'; } },
                { data: 'ip', render: function (d) { return copyBtn(d); } },
                { data: 'port', defaultContent: '' },
                { data: 'asn', defaultContent: '' },
                { data: 'geo', defaultContent: '', render: function (d) { return escapeHtml(d); } },
                { data: 'hostname', defaultContent: '', render: function (d) { return escapeHtml(d); } },
                { data: 'tag', defaultContent: '', render: function (d) { return escapeHtml(d); } },
                { data: 'severity', defaultContent: '', render: function (d) {
                    if (!d) return '';
                    var cls = d === 'high' ? 'bg-danger' : d === 'medium' ? 'bg-warning text-dark' : 'bg-secondary';
                    return '<span class="badge ' + cls + '">' + escapeHtml(d) + '</span>';
                }},
                { data: 'raw_data', orderable: false, render: function (d) {
                    if (!d) return '';
                    var json = JSON.stringify(d, null, 2);
                    var b64 = btoa(unescape(encodeURIComponent(json)));
                    var preview = JSON.stringify(d).substring(0, 60) + '...';
                    return '<button class="btn btn-sm btn-outline-secondary ss-expand" ' +
                           'data-json-b64="' + b64 + '">Expand</button>' +
                           '<span class="text-muted small ms-1">' + escapeHtml(preview) + '</span>';
                }}
            ],
            order: [[0, 'desc']],
            language: {
                emptyTable: 'No Shadowserver matches for this case\'s indicators',
                search: 'Filter:',
                processing: '<div class="spinner-border spinner-border-sm" role="status"></div> Loading...'
            },
            initComplete: function (settings, json) {
                // Update badge with hit count
                var badge = document.getElementById('ss-badge');
                if (badge && json.recordsTotal > 0) {
                    badge.textContent = json.recordsTotal.toLocaleString();
                    badge.style.display = 'inline';
                }
                // #17: Indicator count feedback
                var feedback = document.getElementById('ss-indicator-feedback');
                if (feedback && json.indicators) {
                    var i = json.indicators;
                    var parts = [];
                    if (i.ips) parts.push(i.ips + ' IP' + (i.ips !== 1 ? 's' : ''));
                    if (i.hostnames) parts.push(i.hostnames + ' hostname' + (i.hostnames !== 1 ? 's' : ''));
                    if (i.asns) parts.push(i.asns + ' ASN' + (i.asns !== 1 ? 's' : ''));
                    feedback.textContent = 'Searched ' + (parts.join(', ') || 'no indicators') +
                        ' — ' + (json.recordsTotal || 0) + ' match' + (json.recordsTotal !== 1 ? 'es' : '');
                }
                addColumnFilters(this.api());
            }
        }));
    }

    // Expand raw_data modal
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.ss-expand');
        if (!btn) return;
        e.preventDefault();
        var json = decodeURIComponent(escape(atob(btn.getAttribute('data-json-b64'))));
        var modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = '<div class="modal-dialog modal-lg">' +
            '<div class="modal-content">' +
            '<div class="modal-header"><h5 class="modal-title">Raw Event Data</h5>' +
            '<button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>' +
            '<div class="modal-body"><pre class="mb-0" style="max-height:70vh;overflow:auto;font-size:0.85rem">' +
            escapeHtml(json) + '</pre></div>' +
            '<div class="modal-footer">' +
            '<button type="button" class="btn btn-sm btn-outline-primary copy-btn" data-copy="' + escapeHtml(json).replace(/"/g, '&quot;') + '">Copy</button>' +
            '<button type="button" class="btn btn-sm btn-secondary" data-bs-dismiss="modal">Close</button></div>' +
            '</div></div>';
        document.body.appendChild(modal);
        var bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        modal.addEventListener('hidden.bs.modal', function () { modal.remove(); });
    });

    // ── Build row detail HTML (shared by click expand + restore) ──
    function buildRowDetail(b64, data) {
        var html = '<div class="row-detail-panel p-3">' +
            '<div class="d-flex justify-content-between align-items-center mb-2">' +
            '<strong class="text-iris-category" style="font-size:0.78rem;text-transform:uppercase;letter-spacing:0.03em">Full Record</strong>' +
            '<button class="btn btn-sm btn-outline-secondary copy-json-btn" ' +
            'data-row-b64="' + b64 + '" title="Copy as JSON">' +
            '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 010 1.5h-1.5a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-1.5a.75.75 0 011.5 0v1.5A1.75 1.75 0 019.25 16h-7.5A1.75 1.75 0 010 14.25z"/><path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0114.25 11h-7.5A1.75 1.75 0 015 9.25zm1.75-.25a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-7.5a.25.25 0 00-.25-.25z"/></svg> Copy JSON</button>' +
            '</div>' +
            '<table class="table table-sm mb-0" style="font-size:0.82rem">';
        for (var key in data) {
            var v = data[key];
            var display = (v !== null && typeof v === 'object') ? JSON.stringify(v) : String(v == null ? '' : v);
            html += '<tr><td class="text-iris-category" style="width:180px;font-weight:600;white-space:nowrap">' +
                escapeHtml(key) + '</td><td style="word-break:break-all">' + escapeHtml(display) + '</td></tr>';
        }
        html += '</table></div>';
        return html;
    }

    // ── Row expand: click row to show full record (#3) ──────────
    document.addEventListener('click', function (e) {
        var tr = e.target.closest('.expandable-row');
        if (!tr) return;
        // Don't expand if clicking a link, button, input, or copy-btn
        if (e.target.closest('a, button, input, .copy-btn')) return;

        var $tr = $(tr);
        // Find which DataTable this row belongs to
        var dtTable = $tr.closest('table').DataTable();
        var row = dtTable.row($tr);

        if (row.child.isShown()) {
            row.child.hide();
            $tr.removeClass('row-expanded');
        } else {
            var b64 = tr.getAttribute('data-row-json');
            if (!b64) return;
            var data;
            try {
                data = JSON.parse(decodeURIComponent(escape(atob(b64))));
            } catch (ex) { return; }
            row.child(buildRowDetail(b64, data)).show();
            $tr.addClass('row-expanded');
        }
    });

    // ── IOC context menu: external lookups (#11) ────────────────
    document.addEventListener('contextmenu', function (e) {
        var td = e.target.closest('#dt-iocs td');
        if (!td) return;
        var tr = td.closest('tr');
        if (!tr) return;
        var $tr = $(tr);
        var dtTable;
        try { dtTable = $('#dt-iocs').DataTable(); } catch (ex) { return; }
        var row = dtTable.row($tr);
        if (!row.data()) return;
        var iocValue = row.data().ioc_value;
        if (!iocValue) return;

        e.preventDefault();
        // Remove any existing context menu
        $('.ioc-context-menu').remove();

        var encoded = encodeURIComponent(iocValue);
        var menu = $('<div class="ioc-context-menu dropdown-menu show" style="position:fixed;z-index:9999"></div>');
        menu.css({ top: e.clientY + 'px', left: e.clientX + 'px' });

        var links = [
            { label: 'VirusTotal', url: 'https://www.virustotal.com/gui/search/' + encoded },
            { label: 'AbuseIPDB', url: 'https://www.abuseipdb.com/check/' + encoded },
            { label: 'Shodan', url: 'https://www.shodan.io/search?query=' + encoded },
            { label: 'Censys', url: 'https://search.censys.io/search?resource=hosts&q=' + encoded },
        ];
        links.forEach(function (lnk) {
            menu.append('<a class="dropdown-item" href="' + lnk.url + '" target="_blank" rel="noopener">' +
                escapeHtml(lnk.label) + '</a>');
        });
        menu.append('<div class="dropdown-divider"></div>');
        menu.append('<a class="dropdown-item copy-btn" href="#" data-copy="' + escapeHtml(iocValue) + '">Copy value</a>');

        $('body').append(menu);

        // Close on click outside
        setTimeout(function () {
            $(document).one('click', function () { menu.remove(); });
        }, 0);
    });

    // ── Tab show → init deferred + adjust columns ───────────────
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(function (tab) {
        tab.addEventListener('shown.bs.tab', function (e) {
            var target = e.target.getAttribute('data-bs-target');
            // Map tab target to entity
            var entityMap = {
                '#tab-iocs': 'iocs',
                '#tab-events': 'events',
                '#tab-tasks': 'tasks',
                '#tab-notes': 'notes',
                '#tab-evidences': 'evidences',
                '#tab-shadowserver': 'shadowserver'
            };
            var entity = entityMap[target];
            if (entity === 'shadowserver') {
                initShadowserver();
            } else if (entity) {
                initDeferred(entity);
            }
            $.fn.dataTable.tables({ visible: true, api: true }).columns.adjust();
        });
    });

    // ── Keyboard shortcuts (#2) ─────────────────────────────────
    var tabButtons = document.querySelectorAll('#entityTabs [data-bs-toggle="tab"]');

    document.addEventListener('keydown', function (e) {
        // Don't trigger if focus is in an input/textarea/select
        var tag = document.activeElement.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

        // Esc closes modals
        if (e.key === 'Escape') {
            var openModal = document.querySelector('.modal.show');
            if (openModal) {
                bootstrap.Modal.getInstance(openModal).hide();
                return;
            }
            // Also close context menu
            $('.ioc-context-menu').remove();
            return;
        }

        // Alt+1 through Alt+7: switch tabs
        if (e.altKey && e.key >= '1' && e.key <= '9') {
            var idx = parseInt(e.key) - 1;
            if (idx < tabButtons.length) {
                e.preventDefault();
                tabButtons[idx].click();
            }
            return;
        }

        // Alt+Left/Right: cycle tabs
        if (e.altKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
            e.preventDefault();
            var activeIdx = -1;
            tabButtons.forEach(function (btn, i) {
                if (btn.classList.contains('active')) activeIdx = i;
            });
            if (activeIdx === -1) return;
            var newIdx;
            if (e.key === 'ArrowRight') {
                newIdx = (activeIdx + 1) % tabButtons.length;
            } else {
                newIdx = (activeIdx - 1 + tabButtons.length) % tabButtons.length;
            }
            tabButtons[newIdx].click();
            return;
        }
    });

    // ── Previous/Next case navigation (#8) ──────────────────────
    var prevBtn = document.getElementById('btn-prev-case');
    var nextBtn = document.getElementById('btn-next-case');
    if (prevBtn || nextBtn) {
        $.getJSON('/api/case-neighbors/' + CASE_ID, function (data) {
            if (data.prev != null && prevBtn) {
                prevBtn.href = '/case/' + data.prev;
                prevBtn.classList.remove('disabled');
                prevBtn.title = 'Case #' + data.prev;
            }
            if (data.next != null && nextBtn) {
                nextBtn.href = '/case/' + data.next;
                nextBtn.classList.remove('disabled');
                nextBtn.title = 'Case #' + data.next;
            }
        });
    }

    // ── Auto-refresh entity tables (preserves expanded rows) ────
    if (refreshInterval > 0) {
        setInterval(function () {
            refreshAllTables(true);
        }, refreshInterval * 1000);
    }
});
