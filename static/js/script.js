// Tab Switching
function switchTab(tabName) {
    // Hide all tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // Highlight selected button
    event.target.classList.add('active');
}

// Search functionality for scenarios
document.addEventListener('DOMContentLoaded', function() {
    const scenarioSearch = document.getElementById('scenario-search');
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
                    const projectCell = row.cells[2]; // Project name column
                    const text = projectCell.textContent.toLowerCase();
                    row.style.display = text.includes(selectedProject) ? '' : 'none';
                }
            });
        });
    }
});

// Compare scenarios modal
function showCompareModal() {
    const checkboxes = document.querySelectorAll('.compare-checkbox:checked');
    if (checkboxes.length !== 2) {
        alert('Please select exactly 2 scenarios to compare');
        return;
    }
    
    const id1 = checkboxes[0].value;
    const id2 = checkboxes[1].value;
    
    // For now, just show which scenarios would be compared
    // In future, could open actual comparison view
    alert(`Compare scenario ${id1} with scenario ${id2}\n\nComparison feature coming soon!`);
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
