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