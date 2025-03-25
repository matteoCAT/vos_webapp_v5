from typing import Optional, Tuple

import httpx
from starlette.authentication import (
    AuthCredentials, AuthenticationBackend, AuthenticationError, BaseUser
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from starlette.status import HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED

from app.config import settings


class User(BaseUser):
    """
    User class for authentication middleware
    """

    def __init__(self, user_id: str, email: str,
                 username: str, role: str,
                 access_token: str, refresh_token: Optional[str] = None):
        self.user_id = user_id
        self.email = email
        self.username = username
        self.role = role
        self.access_token = access_token
        self.refresh_token = refresh_token

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.username

    @property
    def identity(self) -> str:
        return self.user_id


class UnauthenticatedUser(BaseUser):
    """
    Represents an unauthenticated user
    """

    @property
    def is_authenticated(self) -> bool:
        return False

    @property
    def display_name(self) -> str:
        return "Guest"

    @property
    def identity(self) -> str:
        return ""


class AuthBackend(AuthenticationBackend):
    """
    Authentication backend that uses session-stored JWT tokens
    """

    async def authenticate(self, request: Request) -> Tuple[AuthCredentials, BaseUser]:
        # Make sure session is available
        if "session" not in request.scope:
            return AuthCredentials(), UnauthenticatedUser()

        # Check if user is already authenticated in session
        if not request.session.get(settings.AUTH_TOKEN_NAME):
            # No token in session, user is not authenticated
            return AuthCredentials(), UnauthenticatedUser()

        # Get tokens from session
        access_token = request.session.get(settings.AUTH_TOKEN_NAME)
        refresh_token = request.session.get(settings.AUTH_REFRESH_TOKEN_NAME)

        # Get user info from session
        user_info = request.session.get("user_info", {})

        if not user_info:
            # Something is wrong, clear session
            request.session.clear()
            return AuthCredentials(), UnauthenticatedUser()

        # Create user object
        user = User(
            user_id=str(user_info.get("id", "")),
            email=user_info.get("email", ""),
            username=user_info.get("username", ""),
            role=user_info.get("role", ""),
            access_token=access_token,
            refresh_token=refresh_token
        )

        # Grant permissions based on role
        # You could extend this to use more granular permissions
        permissions = ["authenticated"]
        if user.role == "admin":
            permissions.extend(["admin"])
        elif user.role == "manager":
            permissions.extend(["manager"])
        elif user.role == "staff":
            permissions.extend(["staff"])

        return AuthCredentials(permissions), user


class ContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle context (company, site) based on URL structure
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Extract path parameters from URL
        path_parts = request.url.path.strip('/').split('/')

        # Initialize context
        request.state.context = {
            "company_id": None,
            "site_id": None,
            "remaining_path": None
        }

        # Extract URL structure
        if len(path_parts) >= 1:
            first_part = path_parts[0]

            # Check if first part is a company ID
            if first_part.startswith('company-'):
                request.state.context["company_id"] = first_part.replace('company-', '')

                # If there's a site ID
                if len(path_parts) >= 2 and path_parts[1].startswith('site-'):
                    request.state.context["site_id"] = path_parts[1].replace('site-', '')

                    # Remaining path (without company and site prefix)
                    if len(path_parts) > 2:
                        request.state.context["remaining_path"] = '/'.join(path_parts[2:])
                else:
                    # Remaining path (without company prefix)
                    if len(path_parts) > 1:
                        request.state.context["remaining_path"] = '/'.join(path_parts[1:])

            # Check if first part is a site ID
            elif first_part.startswith('site-'):
                request.state.context["site_id"] = first_part.replace('site-', '')

                # Remaining path (without site prefix)
                if len(path_parts) > 1:
                    request.state.context["remaining_path"] = '/'.join(path_parts[1:])
            else:
                # No company or site in URL, regular path
                request.state.context["remaining_path"] = '/'.join(path_parts)

        # Process request with the context
        response = await call_next(request)
        return response


class PermissionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check permissions based on URL context (company, site)
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Skip permission check for public routes
        if request.url.path.startswith('/auth/') or request.url.path.startswith('/static/'):
            return await call_next(request)

        # Check if user is authenticated
        if "user" not in request.scope or not request.user.is_authenticated:
            if "session" in request.scope:
                request.session["messages"] = [
                    {"type": "error", "text": "Please log in to access this page"}
                ]
            return RedirectResponse('/auth/login', status_code=302)

        # Get context
        context = getattr(request.state, 'context', {})
        company_id = context.get('company_id')
        site_id = context.get('site_id')

        # If company or site is specified, check permissions
        if company_id or site_id:
            # For now, just check if the user has access to the site
            # In a real application, you would query the API to check permissions
            if site_id:
                try:
                    # Import here to avoid circular import
                    from app.api.sites_client import get_sites_client
                    sites_client = get_sites_client(request)

                    # Get site details
                    site = await sites_client.get_site(site_id)

                    # Check if site exists and user has access
                    if not site:
                        if "session" in request.scope:
                            request.session["messages"] = [
                                {"type": "error", "text": "Site not found or you don't have access"}
                            ]
                        return RedirectResponse('/dashboard', status_code=302)

                except Exception as e:
                    if "session" in request.scope:
                        request.session["messages"] = [
                            {"type": "error", "text": f"Error accessing site: {str(e)}"}
                        ]
                    return RedirectResponse('/dashboard', status_code=302)

        # Continue with the request
        return await call_next(request)


class APIExceptionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle API exceptions
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        try:
            response = await call_next(request)
            return response

        except httpx.HTTPStatusError as exc:
            # Handle API HTTP errors

            if exc.response.status_code == HTTP_401_UNAUTHORIZED:
                # Try to refresh the token if available
                if "user" in request.scope and request.user.is_authenticated and request.user.refresh_token:
                    try:
                        # Import here to avoid circular import
                        from app.api.auth_client import get_auth_client
                        auth_client = get_auth_client(request)

                        # Refresh token
                        tokens = await auth_client.refresh_token()

                        # Update tokens in session
                        if "session" in request.scope:
                            from app.config import settings
                            request.session[settings.AUTH_TOKEN_NAME] = tokens["access_token"]
                            request.session[settings.AUTH_REFRESH_TOKEN_NAME] = tokens["refresh_token"]

                            # Add info message to session
                            request.session["messages"] = [
                                {"type": "info", "text": "Your session has been refreshed"}
                            ]

                            # Redirect to the same page to retry with new token
                            return RedirectResponse(url=request.url.path, status_code=302)
                    except Exception as refresh_error:
                        print(f"Error refreshing token in middleware: {refresh_error}")
                        # Continue with normal unauthorized flow if refresh fails

                # Token refresh failed or wasn't possible, clear session and redirect to login
                if "session" in request.scope:
                    request.session.clear()

                    # Add error message to session
                    request.session["messages"] = [
                        {"type": "error", "text": "Your session has expired. Please log in again."}
                    ]

                # If AJAX request, return JSON response
                if request.headers.get("hx-request") == "true":
                    return JSONResponse(
                        {"error": "Session expired", "redirect": "/auth/login"},
                        status_code=HTTP_401_UNAUTHORIZED
                    )

                return RedirectResponse(url="/auth/login", status_code=302)

            elif exc.response.status_code == HTTP_403_FORBIDDEN:
                # User doesn't have permission
                error_msg = "You don't have permission to access this resource"

                # Add error message to session
                if "session" in request.scope:
                    request.session["messages"] = [
                        {"type": "error", "text": error_msg}
                    ]

                # If AJAX request, return JSON response
                if request.headers.get("hx-request") == "true":
                    return JSONResponse(
                        {"error": error_msg},
                        status_code=HTTP_403_FORBIDDEN
                    )

                # Redirect to dashboard or error page
                return RedirectResponse(url="/dashboard", status_code=302)

            # For other API errors, log and add message
            try:
                error_data = await exc.response.json()
                error_msg = error_data.get("detail", str(exc))
            except Exception:
                error_msg = str(exc)

            # Add error message to session
            if "session" in request.scope:
                request.session["messages"] = [
                    {"type": "error", "text": error_msg}
                ]

            # If AJAX request, return JSON response
            if request.headers.get("hx-request") == "true":
                return JSONResponse(
                    {"error": error_msg},
                    status_code=exc.response.status_code
                )

            # Redirect to previous page or dashboard
            referer = request.headers.get("referer")
            redirect_url = referer if referer else "/dashboard"
            return RedirectResponse(url=redirect_url, status_code=302)

        except Exception as exc:
            # Handle general exceptions
            error_msg = str(exc)

            # Add error message to session
            if "session" in request.scope:
                request.session["messages"] = [
                    {"type": "error", "text": f"An unexpected error occurred: {error_msg}"}
                ]

            # If AJAX request, return JSON response
            if request.headers.get("hx-request") == "true":
                return JSONResponse(
                    {"error": error_msg},
                    status_code=500
                )

            # Redirect to previous page or dashboard
            referer = request.headers.get("referer")
            redirect_url = referer if referer else "/dashboard"
            return RedirectResponse(url=redirect_url, status_code=302)