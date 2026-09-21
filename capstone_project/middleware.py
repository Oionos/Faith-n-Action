from django.shortcuts import redirect
from django.urls import reverse
from datetime import datetime, timedelta
from django.conf import settings

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
        # Process the request first
        response = self.get_response(request)
        
        # If the user is authenticated, refresh their session
        if request.user.is_authenticated:
            # Set session expiry to SESSION_COOKIE_AGE from settings
            if not request.session.get('last_activity'):
                # First request after login, initialize last_activity
                request.session['last_activity'] = datetime.now().timestamp()
            else:
                # Update last_activity timestamp on each request
                request.session['last_activity'] = datetime.now().timestamp()
            
            # Ensure the session doesn't expire during active use
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            request.session.modified = True
            
        return response