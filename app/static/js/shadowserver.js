/* Shadowserver Data Explorer */

document.addEventListener('DOMContentLoaded', function () {

    // ── Helpers ──────────────────────────────────────────────────

    function escapeHtml(s) {
        if (s === null || s === undefined) return '';
        var div = document.createElement('div');
        div.textContent = String(s);
        return div.innerHTML;
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

    // ── Copy to clipboard ────────────────────────────────────────
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.copy-btn');
        if (!btn) return;
        e.preventDefault();
        navigator.clipboard.writeText(btn.getAttribute('data-copy')).then(function () {
            btn.title = 'Copied!';
            setTimeout(function () { btn.title = 'Copy'; }, 1500);
        });
    });

    // ── Column filters ───────────────────────────────────────────
    function addColumnFilters(dt) {
        var headerRow = $(dt.table().header()).find('tr');
        var filterRow = $('<tr class="dt-column-filters"></tr>');
        dt.columns().every(function (idx) {
            var col = this;
            var th = $(headerRow.find('th').eq(idx));
            var td = $('<th></th>');
            if (col.dataSrc() === 'raw_data' || th.text() === 'Actions' || th.text() === '' || th.text() === 'Details') {
                filterRow.append(td);
                return;
            }
            var input = $('<input type="text" class="form-control form-control-sm col-filter-input" placeholder="' + th.text() + '...">');
            td.append(input);
            filterRow.append(td);
            var timer;
            input.on('keyup change clear', function () {
                var val = this.value;
                clearTimeout(timer);
                timer = setTimeout(function () {
                    if (col.search() !== val) { col.search(val).draw(); }
                }, 300);
            });
            input.on('click', function (e) { e.stopPropagation(); });
        });
        headerRow.after(filterRow);
    }

    // ── Load stats + report types ────────────────────────────────
    $.getJSON('/api/shadowserver/stats', function (data) {
        $('#stat-total').text(data.total_events != null ? data.total_events.toLocaleString() : '0');
        $('#stat-types').text(data.report_types || '0');
        if (data.earliest_date && data.latest_date) {
            $('#stat-range').text(data.earliest_date + ' to ' + data.latest_date);
        } else {
            $('#stat-range').text('No data');
        }

        // Last run
        if (data.recent_runs && data.recent_runs.length > 0) {
            var last = data.recent_runs[0];
            var statusClass = last.status === 'success' ? 'text-success' : 'text-danger';
            var time = last.run_finished || last.run_started || '-';
            $('#stat-last-run').html('<span class="' + statusClass + '">' + escapeHtml(last.status) + '</span> ' + escapeHtml(time));
        }

        // Ingestion log table
        var tbody = $('#ingestion-log tbody');
        (data.recent_runs || []).forEach(function (r) {
            var statusBadge = r.status === 'success'
                ? '<span class="badge bg-success">success</span>'
                : r.status === 'running'
                ? '<span class="badge bg-warning">running</span>'
                : '<span class="badge bg-danger">' + escapeHtml(r.status) + '</span>';
            tbody.append('<tr>' +
                '<td>' + escapeHtml(r.run_started) + '</td>' +
                '<td>' + escapeHtml(r.run_finished || '-') + '</td>' +
                '<td>' + statusBadge + '</td>' +
                '<td>' + (r.reports_found || 0) + '</td>' +
                '<td>' + (r.events_ingested || 0) + '</td>' +
                '<td>' + (r.events_skipped || 0) + '</td>' +
                '<td>' + escapeHtml(r.error_message || '') + '</td>' +
            '</tr>');
        });
    });

    // Populate report type filter
    $.getJSON('/api/shadowserver/report-types', function (types) {
        var sel = $('#filter-type');
        types.forEach(function (t) {
            sel.append('<option value="' + escapeHtml(t) + '">' + escapeHtml(t) + '</option>');
        });
    });

    // ── Column-to-index map for ordering ─────────────────────────
    var colMap = {
        0: 'report_date', 1: 'report_type', 2: 'ip', 3: 'port',
        4: 'asn', 5: 'geo', 6: 'hostname', 7: 'tag', 8: 'severity',
    };

    // ── DataTable init ───────────────────────────────────────────
    var dt = new DataTable('#ss-table', {
        serverSide: true,
        processing: true,
        pageLength: 25,
        dom: 'Bfrtip',
        buttons: ['csv', 'copy'],
        autoWidth: false,
        order: [[0, 'desc']],
        ajax: {
            url: '/api/dt/shadowserver',
            data: function (d) {
                d.report_type = $('#filter-type').val();
                d.date_from = $('#filter-from').val();
                d.date_to = $('#filter-to').val();
                // Map column index to DB column name
                if (d.order && d.order.length > 0) {
                    d.order_column = colMap[d.order[0].column] || 'report_date';
                    d.order_dir = d.order[0].dir || 'desc';
                }
            },
            dataSrc: 'data'
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
        language: {
            emptyTable: 'No Shadowserver events found',
            search: 'Search:',
            processing: '<div class="spinner-border spinner-border-sm" role="status"></div> Loading...'
        },
        initComplete: function () {
            addColumnFilters(this.api());
        }
    });

    // ── Filter form ──────────────────────────────────────────────
    $('#ss-filters').on('submit', function (e) {
        e.preventDefault();
        dt.ajax.reload();
    });

    $('#btn-reset').on('click', function () {
        $('#filter-type').val('');
        $('#filter-from').val('');
        $('#filter-to').val('');
        dt.ajax.reload();
    });

    // ── Expand raw_data ──────────────────────────────────────────
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
        modal.addEventListener('hidden.bs.modal', function () {
            modal.remove();
        });
    });
});
