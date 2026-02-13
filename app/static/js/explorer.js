/* IRIS Data Explorer — Main application logic */

document.addEventListener('DOMContentLoaded', function () {
    // Theme toggle
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

    // Entity badge click → switch tab
    document.querySelectorAll('.entity-badge').forEach(function (badge) {
        badge.addEventListener('click', function () {
            var tabKey = this.getAttribute('data-tab');
            var tabBtn = document.querySelector('[data-bs-target="#tab-' + tabKey + '"]');
            if (tabBtn) tabBtn.click();
        });
    });

    // Initialize DataTables if CASE_DATA exists
    if (typeof CASE_DATA === 'undefined') return;

    var dtDefaults = {
        pageLength: 25,
        dom: 'Bfrtip',
        buttons: ['csv', 'copy'],
        order: [[0, 'desc']],
        autoWidth: false,
        language: {
            emptyTable: 'No data available',
            search: 'Filter:'
        }
    };

    function val(obj, keys) {
        // Try multiple key names, return first truthy value
        for (var i = 0; i < keys.length; i++) {
            var v = obj[keys[i]];
            if (v !== undefined && v !== null) return v;
        }
        return '';
    }

    function truncate(s, len) {
        if (!s) return '';
        s = String(s);
        return s.length > len ? s.substring(0, len) + '...' : s;
    }

    function escapeHtml(s) {
        if (!s) return '';
        var div = document.createElement('div');
        div.textContent = String(s);
        return div.innerHTML;
    }

    // Assets
    initTable('#dt-assets', CASE_DATA.assets || [], [
        { data: function (r) { return val(r, ['asset_id']); } },
        { data: function (r) { return escapeHtml(val(r, ['asset_name'])); } },
        { data: function (r) { return escapeHtml(val(r, ['asset_ip'])); } },
        { data: function (r) { return escapeHtml(val(r, ['asset_domain'])); } },
        { data: function (r) { return val(r, ['asset_type_id', 'asset_type']); } },
        { data: function (r) { return val(r, ['asset_compromise_status_id', 'asset_compromise_status']); } },
        { data: function (r) { return escapeHtml(truncate(val(r, ['asset_description']), 200)); } },
        { data: function (r) { return val(r, ['date_added']); } }
    ]);

    // IOCs
    initTable('#dt-iocs', CASE_DATA.iocs || [], [
        { data: function (r) { return val(r, ['ioc_id']); } },
        { data: function (r) { return escapeHtml(val(r, ['ioc_value'])); } },
        { data: function (r) { return val(r, ['ioc_type_id', 'ioc_type']); } },
        { data: function (r) { return val(r, ['ioc_tlp_id', 'ioc_tlp']); } },
        { data: function (r) { return escapeHtml(val(r, ['ioc_tags'])); } },
        { data: function (r) { return escapeHtml(truncate(val(r, ['ioc_description']), 200)); } }
    ]);

    // Events
    initTable('#dt-events', CASE_DATA.events || [], [
        { data: function (r) { return val(r, ['event_id']); } },
        { data: function (r) { return val(r, ['event_date']); } },
        { data: function (r) { return escapeHtml(val(r, ['event_title'])); } },
        { data: function (r) { return escapeHtml(val(r, ['event_source'])); } },
        { data: function (r) { return escapeHtml(val(r, ['event_tags'])); } },
        { data: function (r) { return escapeHtml(truncate(val(r, ['event_content'])), 200); } }
    ]);

    // Tasks
    initTable('#dt-tasks', CASE_DATA.tasks || [], [
        { data: function (r) { return val(r, ['task_id', 'id']); } },
        { data: function (r) { return escapeHtml(val(r, ['task_title'])); } },
        { data: function (r) { return val(r, ['task_status_id', 'task_status']); } },
        { data: function (r) { return escapeHtml(val(r, ['task_tags'])); } },
        { data: function (r) { return val(r, ['task_open_date']); } },
        { data: function (r) { return val(r, ['task_close_date']); } },
        { data: function (r) { return escapeHtml(truncate(val(r, ['task_description']), 200)); } }
    ]);

    // Notes
    initTable('#dt-notes', CASE_DATA.notes || [], [
        { data: function (r) { return val(r, ['note_id']); } },
        { data: function (r) { return escapeHtml(val(r, ['note_title'])); } },
        { data: function (r) { return val(r, ['note_creationdate']); } },
        { data: function (r) { return val(r, ['note_lastupdate']); } },
        { data: function (r) { return escapeHtml(truncate(val(r, ['note_content']), 300)); } }
    ]);

    // Evidences
    initTable('#dt-evidences', CASE_DATA.evidences || [], [
        { data: function (r) { return val(r, ['evidence_id', 'id']); } },
        { data: function (r) { return escapeHtml(val(r, ['filename'])); } },
        { data: function (r) { return escapeHtml(val(r, ['file_hash'])); } },
        { data: function (r) { return val(r, ['file_size']); } },
        { data: function (r) { return val(r, ['date_added']); } },
        { data: function (r) { return escapeHtml(truncate(val(r, ['file_description']), 200)); } }
    ]);

    // Adjust columns on tab show (DataTables needs this for hidden tabs)
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(function (tab) {
        tab.addEventListener('shown.bs.tab', function () {
            $.fn.dataTable.tables({ visible: true, api: true }).columns.adjust();
        });
    });

    function initTable(selector, data, columns) {
        if (!data || data.length === 0) {
            // Still init empty table for consistent UI
            new DataTable(selector, Object.assign({}, dtDefaults, {
                data: [],
                columns: columns
            }));
            return;
        }
        new DataTable(selector, Object.assign({}, dtDefaults, {
            data: data,
            columns: columns
        }));
    }
});
