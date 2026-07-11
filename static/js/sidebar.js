function initSidebars() {
    function setupSidebar(sidebarId) {
        const sidebar = document.getElementById(sidebarId);
        if (!sidebar) return;

        // Check if already initialized to avoid duplicate listeners
        if (sidebar.dataset.jsInitialized) return;

        let closeTimeout;

        sidebar.addEventListener('mouseenter', function() {
            if (closeTimeout) {
                clearTimeout(closeTimeout);
                closeTimeout = null;
            }
            sidebar.classList.add('sidebar-open');
        });

        sidebar.addEventListener('mouseleave', function() {
            closeTimeout = setTimeout(function() {
                sidebar.classList.remove('sidebar-open');
            }, 300); 
        });

        sidebar.dataset.jsInitialized = "true";
    }

    setupSidebar('category-sidebar');
    setupSidebar('filter-sidebar');
}

// Re-initialize on page load and every HTMX load
document.addEventListener('DOMContentLoaded', initSidebars);

if (typeof htmx !== 'undefined') {
    htmx.onLoad(function() {
        initSidebars();
    });
}

// Mobile sidebar toggle logic
window.toggleSidebar = function(sidebarId) {
    const sidebar = document.getElementById(sidebarId);
    if (sidebar) {
        // Close the other sidebar if open
        const otherId = sidebarId === 'category-sidebar' ? 'filter-sidebar' : 'category-sidebar';
        const otherSidebar = document.getElementById(otherId);
        if (otherSidebar) {
            otherSidebar.classList.remove('sidebar-open');
        }
        
        sidebar.classList.toggle('sidebar-open');
    }
};

// Close sidebars when clicking outside on mobile
document.addEventListener('click', function(event) {
    if (window.innerWidth <= 768) {
        const catSidebar = document.getElementById('category-sidebar');
        const filSidebar = document.getElementById('filter-sidebar');
        
        // If clicking inside a sidebar or on a toggle button, ignore
        if (event.target.closest('.sidebar-panel') || event.target.closest('[onclick^="toggleSidebar"]')) {
            return;
        }

        if (catSidebar && catSidebar.classList.contains('sidebar-open')) {
            catSidebar.classList.remove('sidebar-open');
        }
        if (filSidebar && filSidebar.classList.contains('sidebar-open')) {
            filSidebar.classList.remove('sidebar-open');
        }
    }
});