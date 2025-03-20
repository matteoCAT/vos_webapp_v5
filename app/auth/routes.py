from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from pathlib import Path

import httpx
from app.api_client import get_api_client
from app.config import settings
from app.utils.form_utils import parse_form_data

# Get base directory path (project root)
BASE_DIR = Path(__file__).parent.parent.parent

# Initialize templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")


async def login_page(request: Request):
    """
    Render login page
    """
    # If user is already authenticated, redirect to dashboard
    if "user" in request.scope and request.user.is_authenticated:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Get any messages from session
    messages = request.session.pop("messages", []) if "session" in request.scope else []

    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "messages": messages}
    )


async def login(request: Request):
    """
    Handle login form submission
    """
    # If user is already authenticated, redirect to dashboard
    if "user" in request.scope and request.user.is_authenticated:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Get form data
    form = await request.form()
    form_data = dict(form)
    email = form_data.get("email")
    password = form_data.get("password")

    if not email or not password:
        # Add error message to session
        if "session" in request.scope:
            request.session["messages"] = [
                {"type": "error", "text": "Email and password are required"}
            ]
        return RedirectResponse(url="/auth/login", status_code=302)

    try:
        # Get API client
        api_client = get_api_client(request)

        # Attempt to login
        auth_data = await api_client.login(email, password)

        # Store tokens in session
        request.session[settings.AUTH_TOKEN_NAME] = auth_data["tokens"]["access_token"]
        request.session[settings.AUTH_REFRESH_TOKEN_NAME] = auth_data["tokens"]["refresh_token"]

        # Store user info in session
        request.session["user_info"] = auth_data["user"]

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"Welcome back, {auth_data['user']['username']}!"}
        ]

        # Redirect to dashboard
        return RedirectResponse(url="/dashboard", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Invalid email or password"

        if e.response.status_code == 401:
            error_msg = "Invalid email or password"
        else:
            # Try to extract error message from response
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", error_msg)
            except Exception:
                pass

        # Add error message to session
        if "session" in request.scope:
            request.session["messages"] = [
                {"type": "error", "text": error_msg}
            ]

        return RedirectResponse(url="/auth/login", status_code=302)

    except Exception as e:
        # Handle other exceptions
        # Add error message to session
        if "session" in request.scope:
            request.session["messages"] = [
                {"type": "error", "text": f"An error occurred: {str(e)}"}
            ]

        return RedirectResponse(url="/auth/login", status_code=302)


async def logout(request: Request):
    """
    Log out the current user
    """
    # If user is not authenticated, redirect to login
    if "user" not in request.scope or not request.user.is_authenticated:
        return RedirectResponse(url="/auth/login", status_code=302)

    try:
        # Get API client
        api_client = get_api_client(request)

        # Log out user in API
        await api_client.logout()

    except Exception:
        # Ignore errors, we'll clear the session anyway
        pass

    # Clear session
    if "session" in request.scope:
        request.session.clear()

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": "You have been logged out successfully"}
        ]

    # Redirect to login page
    return RedirectResponse(url="/auth/login", status_code=302)


async def forgot_password_page(request: Request):
    """
    Render forgot password page
    """
    # If user is already authenticated, redirect to dashboard
    if "user" in request.scope and request.user.is_authenticated:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Get any messages from session
    messages = request.session.pop("messages", []) if "session" in request.scope else []

    return templates.TemplateResponse(
        "auth/forgot_password.html",
        {"request": request, "messages": messages}
    )


async def forgot_password(request: Request):
    """
    Handle forgot password form submission

    Note: Actual implementation would depend on your API's password reset functionality
    """
    # If user is already authenticated, redirect to dashboard
    if "user" in request.scope and request.user.is_authenticated:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Get form data
    form = await request.form()
    form_data = dict(form)
    email = form_data.get("email")

    if not email:
        # Add error message to session
        if "session" in request.scope:
            request.session["messages"] = [
                {"type": "error", "text": "Email is required"}
            ]
        return RedirectResponse(url="/auth/forgot-password", status_code=302)

    # Add success message
    # Note: For security reasons, always show success even if email doesn't exist
    if "session" in request.scope:
        request.session["messages"] = [
            {"type": "success",
             "text": "If an account exists with that email, password reset instructions have been sent"}
        ]

    # Redirect to login page
    return RedirectResponse(url="/auth/login", status_code=302)


# Define routes
routes = [
    Route("/login", endpoint=login_page, methods=["GET"]),
    Route("/login", endpoint=login, methods=["POST"]),
    Route("/logout", endpoint=logout, methods=["GET"]),
    Route("/forgot-password", endpoint=forgot_password_page, methods=["GET"]),
    Route("/forgot-password", endpoint=forgot_password, methods=["POST"]),
]