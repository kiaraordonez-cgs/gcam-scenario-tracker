console.log('GCAM Scenario Tracker loaded');

// =============================================================================
// Table Sorting
// =============================================================================
function setupTableSorting() {
    console.log('Setting up table sorting...');
    document.querySelectorAll('table.data-table thead th.sortable').forEach(th => {
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
                const aText = (a.cells[columnIndex]?.textContent || '').trim().toLowerCase();
                const bText = (b.cells[columnIndex]?.textContent || '').trim().toLowerCase();
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
        
        const headerRow = thead.querySelector('tr');
        const filterRow = document.createElement('tr');
        filterRow.className = 'filter-row';
        
        headerRow.querySelectorAll('th').forEach((th, colIdx) => {
            const filterCell = document.createElement('th');
            
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
                const cell = row.cells[colIdx];
                if (cell) {
                    const val = cell.textContent.trim();
                    if (val && val !== '') values.add(val);
                }
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

function applyFilters(table) {
    const filters = Array.from(table.querySelectorAll('.filter-row .column-filter'));
    const rows = table.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        let show = true;
        filters.forEach(filter => {
            const val = filter.value;
            if (!val) return;
            const colIdx = parseInt(filter.dataset.columnIndex);
            const cell = row.cells[colIdx];
            if (!cell || cell.textContent.trim() !== val) show = false;
        });
        row.style.display = show ? '' : 'none';
    });
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
function deleteScenario(scenarioId, scenarioName) {
    if (!confirm(`Delete scenario "${scenarioName}"?\n\nThis cannot be undone.`)) return;
    
    fetch(`/delete_scenario/${scenarioId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(err => {
            alert('Error deleting scenario');
            console.error(err);
        });
}

// =============================================================================
// Initialize
// =============================================================================
document.addEventListener('DOMContentLoaded', function() {
    setupTableSorting();
    setupColumnFilters();
});
