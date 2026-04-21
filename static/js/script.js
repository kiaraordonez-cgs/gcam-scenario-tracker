// Tab Switching
document.addEventListener('DOMContentLoaded', function() {
    // Tab switching functionality
    const tabButtons = document.querySelectorAll('.tab-btn');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            
            // Remove active class from all buttons and content
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked button and corresponding content
            this.classList.add('active');
            document.getElementById(tabName + '-tab').classList.add('active');
        });
    });
    
    // Search functionality for scenarios
    if (scenarioSearch) {
        scenarioSearch.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#scenarios-table tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    }
    
    // Search functionality for input files
    const inputSearch = document.getElementById('input-search');
    if (inputSearch) {
        inputSearch.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#inputs-table tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    }
    
    // Project filter
    const projectFilter = document.getElementById('project-filter');
    if (projectFilter) {
        projectFilter.addEventListener('change', function(e) {
            const selectedProject = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#scenarios-table tbody tr');
            
            rows.forEach(row => {
                if (!selectedProject) {
                    row.style.display = '';
                } else {
                    const projectCell = row.cells[3]; // Project name column (after checkbox)
                    const text = projectCell.textContent.toLowerCase();
                    row.style.display = text.includes(selectedProject) ? '' : 'none';
                }
            });
        });
    }
    
    // Table Sorting Setup
    document.querySelectorAll('th.sortable').forEach((header) => {
        // Make it obvious these are clickable
        header.style.cursor = 'pointer';
        header.title = 'Click to sort';
        
        header.addEventListener('click', function() {
            console.log('Sorting column:', this.textContent);
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            // Determine if this column is currently sorted
            const currentSort = this.dataset.sort || 'none';
            const newSort = currentSort === 'asc' ? 'desc' : 'asc';
            console.log('Sort direction:', newSort);
            
            // Reset all headers in this table
            table.querySelectorAll('th.sortable').forEach(th => {
                delete th.dataset.sort;
                th.style.fontWeight = 'normal';
            });
            
            // Mark this header as sorted
            this.dataset.sort = newSort;
            this.style.fontWeight = 'bold';
            
            // Get column index
            const headerIndex = Array.from(this.parentElement.children).indexOf(this);
            
            // Sort rows
            rows.sort((a, b) => {
                let aValue = a.children[headerIndex]?.textContent.trim() || '';
                let bValue = b.children[headerIndex]?.textContent.trim() || '';
                
                // Try to parse as numbers
                const aNum = parseFloat(aValue);
                const bNum = parseFloat(bValue);
                
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return newSort === 'asc' ? aNum - bNum : bNum - aNum;
                }
                
                // String comparison
                if (newSort === 'asc') {
                    return aValue.localeCompare(bValue);
                } else {
                    return bValue.localeCompare(aValue);
                }
            });
            
            // Re-append rows in new order
            rows.forEach(row => tbody.appendChild(row));
            console.log('Sorted', rows.length, 'rows');
        });
    });
});

// Compare scenarios modal
function showCompareModal() {
    const checkboxes = document.querySelectorAll('.compare-checkbox:checked');
    console.log('Compare button clicked, found checkboxes:', checkboxes.length);
    
    if (checkboxes.length < 2) {
        alert('Please select at least 2 scenarios to compare');
        return;
    }
    
    // Get all selected scenario IDs
    const scenarioIds = Array.from(checkboxes).map(cb => cb.value);
    console.log('Scenario IDs:', scenarioIds);
    
    // Redirect to comparison page
    const url = `/compare_scenarios?ids=${scenarioIds.join(',')}`;
    console.log('Redirecting to:', url);
    window.location.href = url;
}
}

// Delete scenario
function deleteScenario(scenarioId, scenarioName) {
    if (!confirm(`Are you sure you want to delete scenario "${scenarioName}"?\n\nThis will also remove all links to input files (but not the input files themselves).`)) {
        return;
    }
    
    // Send delete request
    fetch(`/delete_scenario/${scenarioId}`, {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Scenario deleted successfully');
            location.reload();
        } else {
            alert('Error deleting scenario: ' + data.error);
        }
    })
    .catch(error => {
        alert('Error deleting scenario: ' + error);
    });
}

console.log('GCAM Scenario Tracker loaded');
