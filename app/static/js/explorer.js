/* IRIS Data Explorer — Main application logic */

document.addEventListener('DOMContentLoaded', function () {
    // ── Theme toggle ────────────────────────────────────────────
    var themeBtn = document.getElementById('theme-toggle');
    var themeIcon = document.getElementById('theme-icon');
    if (themeBtn) {
        var saved = localStorage.getItem('ide-theme') || 'dark';
        document.documentElement.setAttribute('data-bs-theme', saved);
        themeIcon.textContent = saved === 'dark' ? '\u2600' : '\u263E';

        themeBtn.addEventListener('click', function () {
            var current = document.documentElement.getAttribute('data-bs-theme');
            var next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-bs-theme', next);
            localStorage.setItem('ide-theme', next);
            themeIcon.textContent = next === 'dark' ? '\u2600' : '\u263E';
        });
    }

    // ── Helpers ──────────────────────────────────────────────────

    function escapeHtml(s) {
        if (s === null || s === undefined) return '';
        var div = document.createElement('div');
        div.textContent = String(s);
        return div.innerHTML;
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

    function irisLink(path, text) {
        if (typeof IRIS_URL === 'undefined') return escapeHtml(text);
        return '<a href="' + escapeHtml(IRIS_URL) + path + '" target="_blank" ' +
               'class="text-decoration-none">' + escapeHtml(text) + '</a>';
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

    // ── Server-side DataTables ──────────────────────────────────
    if (typeof CASE_ID === 'undefined') return;

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
        { data: 'asset_description', render: function (d) { return escapeHtml(truncate(d, 200)); } },
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
        { data: 'ioc_description', render: function (d) { return escapeHtml(truncate(d, 200)); } }
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
        { data: 'event_content', render: function (d) { return escapeHtml(truncate(d, 200)); } }
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
        { data: 'task_description', defaultContent: '', render: function (d) { return escapeHtml(truncate(d, 200)); } }
    ]);

    // Notes
    tables.notes = initTable('#dt-notes', 'notes', [
        { data: 'note_id', render: function (d, t, r) {
            return irisLink('/case/notes?cid=' + CASE_ID, d);
        }},
        { data: 'note_title', render: function (d) { return escapeHtml(d); } },
        { data: 'note_creationdate', defaultContent: '' },
        { data: 'note_lastupdate', defaultContent: '' },
        { data: 'note_content', defaultContent: '', render: function (d) { return escapeHtml(truncate(d, 300)); } }
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
        { data: 'file_description', defaultContent: '', render: function (d) { return escapeHtml(truncate(d, 200)); } }
    ]);

    // ── Tab show → adjust columns + lazy-load ───────────────────
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(function (tab) {
        tab.addEventListener('shown.bs.tab', function () {
            $.fn.dataTable.tables({ visible: true, api: true }).columns.adjust();
        });
    });

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
