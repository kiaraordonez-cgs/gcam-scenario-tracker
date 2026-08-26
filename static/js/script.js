console.log('GCAM Scenario Tracker loaded');

function notify(message, kind) {
    let host = document.getElementById('toast-host');
    if (!host) {
        host = document.createElement('div');
        host.id = 'toast-host';
        document.body.appendChild(host);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${kind === 'success' ? 'success' : 'error'}`;
    toast.textContent = message;

    const close = document.createElement('button');
    close.className = 'toast-close';
    close.type = 'button';
    close.textContent = '×';
    close.setAttribute('aria-label', 'Dismiss');
    close.addEventListener('click', () => toast.remove());
    toast.appendChild(close);

    host.appendChild(toast);
    if (kind === 'success') setTimeout(() => toast.remove(), 4000);
}

// =============================================================================
// Table Sorting
// =============================================================================

function sortKey(cell) {
    if (!cell) return '';
    const raw = cell.dataset.sortValue;
    if (raw !== undefined && raw !== '') return raw.trim().toLowerCase();
    return (cell.textContent || '').trim().toLowerCase();
}

function setupTableSorting() {
    document.querySelectorAll('table.data-table thead th.sortable').forEach(th => {
        if (th.dataset.sortBound) return;
        th.dataset.sortBound = '1';

        th.addEventListener('click', function() {
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const columnIndex = Array.from(this.parentNode.children).indexOf(this);
            
            // Determine sort direction
            const currentSort = this.getAttribute('data-sort');
            const isAsc = currentSort !== 'asc';
            
            // Clear all sort indicators in this table
            table.querySelectorAll('th.sortable').forEach(h => h.removeAttribute('data-sort'));
            this.setAttribute('data-sort', isAsc ? 'asc' : 'desc');
            
            // Sort rows
            const rows = Array.from(tbody.querySelectorAll('tr'));
            rows.sort((a, b) => {
                const aText = sortKey(a.cells[columnIndex]);
                const bText = sortKey(b.cells[columnIndex]);
                const aNum = parseFloat(aText);
                const bNum = parseFloat(bText);
                
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return isAsc ? aNum - bNum : bNum - aNum;
                }
                return isAsc ? aText.localeCompare(bText) : bText.localeCompare(aText);
            });
            
            rows.forEach(row => tbody.appendChild(row));
        });
    });
    console.log('Sorting setup complete');
}

// =============================================================================
// Column Dropdown Filters
// =============================================================================
function setupColumnFilters() {
    document.querySelectorAll('table.data-table').forEach(table => {
        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');
        if (!tbody || tbody.rows.length === 0) return;
        const existing = thead.querySelector('tr.filter-row');
        if (existing) existing.remove();

        const headerRow = thead.querySelector('tr');
        const filterRow = document.createElement('tr');
        filterRow.className = 'filter-row';

        headerRow.querySelectorAll('th').forEach((th, colIdx) => {
            const filterCell = document.createElement('th');

            th.classList.forEach(c => {
                if (c.startsWith('col-')) filterCell.classList.add(c);
            });

            // Skip checkbox and actions columns only
            const text = th.textContent.trim();
            if (th.querySelector('input[type="checkbox"]') || text === 'Actions') {
                filterCell.innerHTML = '';
                filterRow.appendChild(filterCell);
                return;
            }
            
            // Collect unique values
            const values = new Set();
            tbody.querySelectorAll('tr').forEach(row => {
                const val = cellFilterText(row.cells[colIdx]);
                if (val) values.add(val);
            });
            
            const select = document.createElement('select');
            select.className = 'column-filter';
            select.dataset.columnIndex = colIdx;
            
            // Default option - clean label, no triangle
            const defaultOpt = document.createElement('option');
            defaultOpt.value = '';
            defaultOpt.textContent = 'Filter';
            select.appendChild(defaultOpt);
            
            // Sorted unique values
            Array.from(values).sort((a, b) => a.localeCompare(b)).forEach(val => {
                const opt = document.createElement('option');
                opt.value = val;
                opt.textContent = val.length > 35 ? val.substring(0, 32) + '...' : val;
                opt.title = val;
                select.appendChild(opt);
            });
            
            select.addEventListener('change', function() {
                this.classList.toggle('active-filter', this.value !== '');
                applyFilters(table);
            });
            filterCell.appendChild(select);
            filterRow.appendChild(filterCell);
        });
        
        thead.appendChild(filterRow);
    });
}

function cellFilterText(cell) {
    if (!cell) return '';
    const select = cell.querySelector('select');
    if (select) return (select.value || '').trim();
    return (cell.textContent || '').trim();
}

function applyRowVisibility(table) {
    if (!table) return;

    const isScenarios = table.id === 'scenarios-table';
    const searchBox = document.getElementById(isScenarios ? 'scenario-search' : 'input-search');
    const term = ((searchBox && searchBox.value) || '').trim().toLowerCase();

    const projectSelect = isScenarios ? document.getElementById('project-filter') : null;
    const project = (projectSelect && projectSelect.value) || '';

    const filters = Array.from(table.querySelectorAll('.filter-row .column-filter'))
        .filter(f => f.value);

    table.querySelectorAll('tbody tr').forEach(row => {
        let show = true;

        if (term && !(row.dataset.search || '').includes(term)) show = false;
        if (show && project && row.dataset.project !== project) show = false;

        if (show) {
            for (const filter of filters) {
                const cell = row.cells[parseInt(filter.dataset.columnIndex, 10)];
                if (cellFilterText(cell) !== filter.value) { show = false; break; }
            }
        }

        row.style.display = show ? '' : 'none';
    });
}

// Kept as an alias: setupColumnFilters and any older callers still say applyFilters.
function applyFilters(table) {
    applyRowVisibility(table);
}

// =============================================================================
// Compare Scenarios
// =============================================================================
function showCompareModal() {
    const checked = document.querySelectorAll('.compare-checkbox:checked');
    if (checked.length < 2) {
        alert('Please select at least 2 scenarios to compare');
        return;
    }
    
    const scenarioIds = Array.from(checked).map(cb => cb.value);
    window.location.href = `/compare_scenarios?ids=${scenarioIds.join(',')}`;
}

// =============================================================================
// Delete Scenario
// =============================================================================
function adjustCount(elementId, delta) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const n = parseInt(el.textContent, 10);
    if (!isNaN(n)) el.textContent = Math.max(0, n + delta);
}

function deleteScenario(scenarioId, scenarioName) {
    if (!confirm(`Delete scenario "${scenarioName}"?\n\nThis cannot be undone.`)) return;

    const row = Array.from(document.querySelectorAll('#scenarios-table tbody tr'))
        .find(r => r.dataset.id === String(scenarioId));
    const parent = row ? row.parentNode : null;
    const anchor = row ? row.nextSibling : null;

    if (row) {
        row.remove();
        adjustCount('scenarios-count', -1);
    }

    fetch(`/delete_scenario/${scenarioId}`, { method: 'POST' })
        .then(res => res.json().catch(() => ({})).then(data => {
            if (!res.ok || !data.success) {
                throw new Error(data.error || `Delete failed (HTTP ${res.status})`);
            }
        }))
        .catch(err => {
            if (row && parent) {
                parent.insertBefore(row, anchor);
                adjustCount('scenarios-count', 1);
            }
            notify(`Could not delete "${scenarioName}": ${err.message}`);
            console.error(err);
        });
}

// =============================================================================
// Initialize
// =============================================================================
document.addEventListener('DOMContentLoaded', function() {
    // Sorting and filters are initialized by loadData() in index.html after AJAX completes
});
