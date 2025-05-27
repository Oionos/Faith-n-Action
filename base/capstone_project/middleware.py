from django.shortcuts import redirect
from django.urls import reverse

class EnsureNotAuthenticatedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        protected_paths = [
            '/dashboard/', '/manage-pending-users/', '/analytics-form/',
            '/analytics-view/', '/approve-user/', '/reject-user/',
            '/promote-user/', '/demote-user/', '/delete-user/'
        ]
        if any(request.path.startswith(path) for path in protected_paths) and not request.user.is_authenticated:
            response = redirect(reverse('sign-in'))
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        response = self.get_response(request)
        return response

class SessionRefreshMiddleware:
    """
    Middleware to refresh the session on each request for authenticated users.
    This helps prevent unexpected logouts during active use of the site.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # If the user is authenticated, refresh their session
        if request.user.is_authenticated:
            request.session.modified = True
            
        return response