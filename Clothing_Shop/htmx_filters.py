def is_htmx_request_allowed(request):
    """
    Determines if HTMX should process a request based on its URL.
    Excludes Django admin URLs from HTMX processing.
    """
    # Exclude admin pages from HTMX processing
    if request.path.startswith('/admin/'):
        return False
    return True
