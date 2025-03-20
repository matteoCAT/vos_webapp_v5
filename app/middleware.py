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
                # Token might be expired, attempt to refresh or redirect to login
                # For now, just clear session and redirect to login
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