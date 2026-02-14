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

    // ── Column filters ───────────────────────────────────────────
    function addColumnFilters(dt) {
        var headerRow = $(dt.table().header()).find('tr');
        var filterRow = $('<tr class="dt-column-filters"></tr>');

        dt.columns().every(function (idx) {
            var col = this;
            var th = $(headerRow.find('th').eq(idx));
            var td = $('<th></th>');

            // Skip non-searchable columns (like "Details" / action buttons)
            if (col.dataSrc() === 'raw_data' || th.text() === 'Actions' || th.text() === '') {
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

    // ── Cases list page (AJAX DataTable) ────────────────────────
    var casesTable = document.getElementById('cases-table');
    if (casesTable && CASE_ID === undefined) {
        var irisUrl = (typeof IRIS_URL !== 'undefined') ? IRIS_URL : '';
        var dt = new DataTable('#cases-table', {
            serverSide: true,
            processing: true,
            pageLength: 25,
            dom: 'Bfrtip',
            buttons: ['csv'],
            autoWidth: false,
            order: [[0, 'desc']],
            initComplete: function () { addColumnFilters(this.api()); },
            ajax: {
                url: '/api/dt/cases',
                dataSrc: 'data'
            },
            columns: [
                { data: 'case_id' },
                { data: 'case_name', render: function (d) { return escapeHtml(d); } },
                { data: 'case_description', render: function (d) { return escapeHtml(truncate(stripHtml(d), 120)); } },
                { data: 'case_soc_id', defaultContent: '' },
                { data: 'open_date', defaultContent: '' },
                { data: 'close_date', defaultContent: '' },
                { data: 'case_id', render: function (d) {
                    return '<a href="/case/' + d + '" class="btn btn-sm btn-primary">Explore</a> ' +
                           '<a href="' + escapeHtml(irisUrl) + '/case?cid=' + d + '" target="_blank" ' +
                           'class="btn btn-sm btn-outline-info" title="Open in IRIS">IRIS</a>';
                }}
            ],
            language: {
                emptyTable: 'No cases found',
                search: 'Filter:',
                processing: '<div class="spinner-border spinner-border-sm" role="status"></div> Loading...'
            }
        });

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

    var dtDefaults = {
        serverSide: true,
        processing: true,
        pageLength: 25,
        dom: 'Bfrtip',
        buttons: ['csv', 'copy'],
        autoWidth: false,
        language: {
            emptyTable: 'No data available',
            search: 'Filter:',
            processing: '<div class="spinner-border spinner-border-sm" role="status"></div> Loading...'
        },
        initComplete: function () {
            addColumnFilters(this.api());
        }
    };

    var tables = {};

    // Assets
    tables.assets = initTable('#dt-assets', 'assets', [
        { data: 'asset_id', render: function (d, t, r) {
            return irisLink('/case/assets?cid=' + CASE_ID, d);
        }},
        { data: 'asset_name', render: function (d) { return escapeHtml(d); } },
        { data: 'asset_ip', render: function (d) { return copyBtn(d); } },
        { data: 'asset_domain', render: function (d) { return copyBtn(d); } },
        { data: 'asset_type_id' },
        { data: 'asset_compromise_status_id' },
        { data: 'asset_description', render: function (d) { return escapeHtml(truncate(stripHtml(d), 200)); } },
        { data: 'date_added' }
    ]);

    // IOCs
    tables.iocs = initTable('#dt-iocs', 'iocs', [
        { data: 'ioc_id', render: function (d, t, r) {
            return irisLink('/case/ioc?cid=' + CASE_ID, d);
        }},
        { data: 'ioc_value', render: function (d) { return copyBtn(d); } },
        { data: 'ioc_type_id' },
        { data: 'ioc_tlp_id' },
        { data: 'ioc_tags', render: function (d) { return escapeHtml(d); } },
        { data: 'ioc_description', render: function (d) { return escapeHtml(truncate(stripHtml(d), 200)); } }
    ]);

    // Events
    tables.events = initTable('#dt-events', 'events', [
        { data: 'event_id', render: function (d, t, r) {
            return irisLink('/case/timeline?cid=' + CASE_ID, d);
        }},
        { data: 'event_date' },
        { data: 'event_title', render: function (d) { return escapeHtml(d); } },
        { data: 'event_source', render: function (d) { return escapeHtml(d); } },
        { data: 'event_tags', render: function (d) { return escapeHtml(d); } },
        { data: 'event_content', render: function (d) { return escapeHtml(truncate(stripHtml(d), 200)); } }
    ]);

    // Tasks
    tables.tasks = initTable('#dt-tasks', 'tasks', [
        { data: 'task_id', defaultContent: '', render: function (d, t, r) {
            var id = d || val(r, ['id']);
            return irisLink('/case/task?cid=' + CASE_ID, id);
        }},
        { data: 'task_title', defaultContent: '', render: function (d) { return escapeHtml(d); } },
        { data: 'task_status_id', defaultContent: '' },
        { data: 'task_tags', defaultContent: '', render: function (d) { return escapeHtml(d); } },
        { data: 'task_open_date', defaultContent: '' },
        { data: 'task_close_date', defaultContent: '' },
        { data: 'task_description', defaultContent: '', render: function (d) { return escapeHtml(truncate(stripHtml(d), 200)); } }
    ]);

    // Notes
    tables.notes = initTable('#dt-notes', 'notes', [
        { data: 'note_id', render: function (d, t, r) {
            return irisLink('/case/notes?cid=' + CASE_ID, d);
        }},
        { data: 'note_title', render: function (d) { return escapeHtml(d); } },
        { data: 'note_creationdate', defaultContent: '' },
        { data: 'note_lastupdate', defaultContent: '' },
        { data: 'note_content', defaultContent: '', render: function (d) { return escapeHtml(truncate(stripHtml(d), 300)); } }
    ]);

    // Evidences
    tables.evidences = initTable('#dt-evidences', 'evidences', [
        { data: 'evidence_id', defaultContent: '', render: function (d, t, r) {
            var id = d || val(r, ['id']);
            return irisLink('/case/evidences?cid=' + CASE_ID, id);
        }},
        { data: 'filename', defaultContent: '', render: function (d) { return escapeHtml(d); } },
        { data: 'file_hash', defaultContent: '', render: function (d) { return copyBtn(d); } },
        { data: 'file_size', defaultContent: '' },
        { data: 'date_added', defaultContent: '' },
        { data: 'file_description', defaultContent: '', render: function (d) { return escapeHtml(truncate(stripHtml(d), 200)); } }
    ]);

    // ── Shadowserver tab (dynamic correlation) ─────────────────
    var ssTable = document.getElementById('dt-shadowserver');
    if (ssTable) {
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
                addColumnFilters(this.api());
            }
        }));

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
                '<div class="modal-footer"><button type="button" class="btn btn-sm btn-secondary" data-bs-dismiss="modal">Close</button></div>' +
                '</div></div>';
            document.body.appendChild(modal);
            var bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            modal.addEventListener('hidden.bs.modal', function () { modal.remove(); });
        });
    }

    // ── Tab show → adjust columns ───────────────────────────────
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(function (tab) {
        tab.addEventListener('shown.bs.tab', function () {
            $.fn.dataTable.tables({ visible: true, api: true }).columns.adjust();
        });
    });

    // ── Auto-refresh entity tables ──────────────────────────────
    if (refreshInterval > 0) {
        setInterval(function () {
            // Reload all initialized tables with cache bust, keep current page
            Object.keys(tables).forEach(function (key) {
                var t = tables[key];
                if (key === 'shadowserver') {
                    t.ajax.url('/api/dt/case/' + CASE_ID + '/shadowserver?refresh=1').load(null, false);
                } else {
                    var baseUrl = '/api/dt/case/' + CASE_ID + '/' + key;
                    t.ajax.url(baseUrl + '?refresh=1').load(null, false);
                }
            });
            lastRefresh = new Date();
        }, refreshInterval * 1000);
    }

    function initTable(selector, entity, columns) {
        return new DataTable(selector, $.extend(true, {}, dtDefaults, {
            ajax: {
                url: '/api/dt/case/' + CASE_ID + '/' + entity,
                dataSrc: 'data'
            },
            columns: columns,
            order: [[0, 'desc']]
        }));
    }
});
