from typing import List, Optional, Union
from starlette.requests import Request
from starlette.responses import RedirectResponse
from functools import wraps

from app.api_client import get_api_client


def permission_required(permissions: Union[str, List[str]]):
    """
    Decorator to check if the current user has the required permissions

    Args:
        permissions: Permission or list of permissions required

    Returns:
        Decorated function
    """
    if isinstance(permissions, str):
        permissions = [permissions]

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                # Add error message to session
                request.session["messages"] = [
                    {"type": "error", "text": "Please log in to access this page"}
                ]

                # Redirect to login page
                return RedirectResponse(url="/auth/login", status_code=302)

            # Check if user has required permissions
            # This is simplified - in a real app, you would check actual permissions
            # For now, we'll just check role
            has_permission = False

            if request.user.role == "admin":
                # Admin has all permissions
                has_permission = True
            elif request.user.role == "manager":
                # Manager has many permissions but not all
                has_permission = not any(p.startswith("admin_") for p in permissions)
            elif request.user.role == "staff":
                # Staff has limited permissions
                has_permission = all(p.startswith("view_") for p in permissions)

            if not has_permission:
                # Add error message to session
                request.session["messages"] = [
                    {"type": "error", "text": "You do not have permission to access this page"}
                ]

                # Redirect to dashboard
                return RedirectResponse(url="/dashboard", status_code=302)

            # User has permission, continue
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def add_message(request: Request, message_type: str, text: str):
    """
    Add a message to the session

    Args:
        request: The current request
        message_type: Message type (success, error, info, warning)
        text: Message text
    """
    messages = request.session.get("messages", [])
    messages.append({"type": message_type, "text": text})
    request.session["messages"] = messages