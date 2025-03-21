import os
from typing import Any, Dict
from pathlib import Path

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from starlette.requests import Request

from app.config import settings
from app.middleware import APIExceptionMiddleware, AuthBackend
from app.auth.routes import routes as auth_routes
from app.dashboard.routes import routes as dashboard_routes
from app.users.routes import routes as users_routes

# Import other route modules as they're created


# Get base directory path (project root)
BASE_DIR = Path(__file__).parent.parent

# Initialize templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Add custom filters or globals to templates
templates.env.globals.update({
    "app_name": settings.APP_NAME,
    "app_version": settings.APP_VERSION,
})

# Configure middleware - order is important!
middleware = [
    Middleware(SessionMiddleware, secret_key=settings.SECRET_KEY),
    Middleware(AuthenticationMiddleware, backend=AuthBackend()),
    Middleware(APIExceptionMiddleware),
]


# Startup event handler
async def startup():
    """Initialize application resources on startup"""
    # Create global httpx client for API calls
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.API_BASE_URL,
        timeout=settings.API_TIMEOUT,
        verify=settings.VERIFY_SSL,
    )

    # Ensure static directories exist
    static_dir = BASE_DIR / "static"
    css_dir = static_dir / "css"
    js_dir = static_dir / "js"
    images_dir = static_dir / "images"

    # Create directories if they don't exist
    for directory in [static_dir, css_dir, js_dir, images_dir]:
        directory.mkdir(exist_ok=True, parents=True)

    # Add a default favicon if one doesn't exist
    favicon_path = images_dir / "favicon.ico"
    if not favicon_path.exists():
        # Create a minimal 16x16 favicon (transparent)
        try:
            with open(favicon_path, "wb") as f:
                f.write(b"\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x18\x00\x30\x00"
                        b"\x00\x00\x16\x00\x00\x00\x28\x00\x00\x00\x10\x00\x00\x00\x20\x00"
                        b"\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        except Exception as e:
            print(f"Warning: Could not create favicon: {e}")

    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")


# Shutdown event handler
async def shutdown():
    """Cleanup application resources on shutdown"""
    await app.state.http_client.aclose()
    print(f"Shutting down {settings.APP_NAME}")


# Root route handler
async def homepage(request: Request):
    """
    Redirect to dashboard if authenticated, otherwise to login page
    """
    if "user" in request.scope and request.user.is_authenticated:
        return RedirectResponse(url="/dashboard/", status_code=302)  # Note the trailing slash
    else:
        return RedirectResponse(url="/auth/login", status_code=302)


# Debug route handler
async def debug_info(request: Request):
    """
    Debug endpoint to check authentication status and session data
    Only available in DEBUG mode
    """
    if not settings.DEBUG:
        return RedirectResponse(url="/", status_code=302)

    info = {
        "authenticated": "user" in request.scope and getattr(request.user, "is_authenticated", False),
        "user_info": {
            "id": getattr(request.user, "user_id", None) if "user" in request.scope else None,
            "username": getattr(request.user, "display_name", None) if "user" in request.scope else None,
            "role": getattr(request.user, "role", None) if "user" in request.scope else None,
        },
        "session_keys": list(request.session.keys()) if "session" in request.scope else [],
        "request_headers": dict(request.headers),
        "request_path": request.url.path,
    }

    # Return JSON in debug mode
    from starlette.responses import JSONResponse
    return JSONResponse(info)


# Site switch handler
async def switch_site(request: Request):
    """
    Handle site switching and redirects back to previous page
    """
    # Get site ID from path params
    site_id = request.path_params.get("site_id")

    # If user is authenticated
    if "user" in request.scope and request.user.is_authenticated and "session" in request.scope:
        # Get API client
        from app.api_client import get_api_client
        api_client = get_api_client(request)

        try:
            # Get site details
            sites = await api_client.get_sites()

            # Find selected site
            for site in sites:
                if str(site.get("id")) == str(site_id):
                    # Store current site in session
                    request.session["current_site_id"] = site.get("id")
                    request.session["current_site_name"] = site.get("name")

                    # Add success message
                    request.session["messages"] = [
                        {"type": "success", "text": f"Switched to {site.get('name')}"}
                    ]
                    break
        except Exception as e:
            # Add error message
            request.session["messages"] = [
                {"type": "error", "text": f"Error switching site: {str(e)}"}
            ]

    # Redirect to previous page or dashboard
    referer = request.headers.get("referer")
    redirect_url = referer if referer else "/dashboard/"
    return RedirectResponse(url=redirect_url, status_code=302)


# Debug sites handler
async def debug_sites(request: Request):
    """
    Debug endpoint to specifically test sites API integration
    Only available in DEBUG mode
    """
    if not settings.DEBUG:
        return RedirectResponse(url="/", status_code=302)

    from app.api_client import get_api_client
    api_client = get_api_client(request)

    response_data = {
        "authenticated": "user" in request.scope and getattr(request.user, "is_authenticated", False),
        "api_base_url": settings.API_BASE_URL,
        "sites_url": f"{settings.API_BASE_URL}/sites",
        "error": None,
        "sites": []
    }

    try:
        # Try to fetch sites directly
        response_data["sites"] = await api_client.get_sites()
    except Exception as e:
        response_data["error"] = str(e)

    # Return JSON in debug mode
    from starlette.responses import JSONResponse
    return JSONResponse(response_data)


# Routes collected from all modules
routes = [
    # Root route
    Route("/", endpoint=homepage),

    # Site switcher route
    Route("/switch-site/{site_id:str}", endpoint=switch_site),

    # Debug routes (only active in DEBUG mode)
    Route("/debug", endpoint=debug_info),
    Route("/debug/sites", endpoint=debug_sites),

    # Mount static files - pointing to project root static folder
    Mount("/static", app=StaticFiles(directory=BASE_DIR / "static"), name="static"),

    # Mount routes from all modules
    Mount("/auth", routes=auth_routes),
    Mount("/dashboard", routes=dashboard_routes),  # Starlette will handle trailing slashes
    Mount("/users", routes=users_routes),
    # Mount other routes as they're created
]

# Create Starlette application
app = Starlette(
    debug=settings.DEBUG,
    routes=routes,
    middleware=middleware,
    on_startup=[startup],
    on_shutdown=[shutdown],
)


# Template context processor - after AuthenticationMiddleware is applied
@app.middleware("http")
async def add_template_context(request, call_next):
    """Add global template context variables"""
    # Initialize context with basic data
    from datetime import datetime
    context = {
        "request": request,
        "messages": [],
        "now": datetime.now()
    }

    # Safely get messages from session if available
    if "session" in request.scope:
        context["messages"] = request.session.pop("messages", [])

    # Add user to context if available
    if "user" in request.scope:
        context["user"] = request.user

    # Store context in request state
    request.state.template_context = context

    return await call_next(request)


# Run the application (for development only)
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )