import os
from typing import Any, Dict
from pathlib import Path
from datetime import datetime

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
from app.middleware import (
    AuthBackend,
    APIExceptionMiddleware,
    ContextMiddleware,
    PermissionMiddleware
)

# Import route modules
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


# Root route handler
async def homepage(request: Request):
    """
    Redirect to dashboard if authenticated, otherwise to login page
    """
    if "user" in request.scope and request.user.is_authenticated:
        return RedirectResponse(url="/dashboard/", status_code=302)
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
        "context": getattr(request.state, "context", {}),
    }

    # Return JSON in debug mode
    from starlette.responses import JSONResponse
    return JSONResponse(info)


# Configure middleware - order is important!
middleware = [
    Middleware(SessionMiddleware, secret_key=settings.SECRET_KEY),
    Middleware(ContextMiddleware),  # Extract hierarchical URL structure
    Middleware(AuthenticationMiddleware, backend=AuthBackend()),
    Middleware(PermissionMiddleware),  # Check permissions based on URL context
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


# Routes collected from all modules
routes = [
    # Root route
    Route("/", endpoint=homepage),

    # Debug route (only active in DEBUG mode)
    Route("/debug", endpoint=debug_info),

    # Mount static files - pointing to project root static folder
    Mount("/static", app=StaticFiles(directory=BASE_DIR / "static"), name="static"),

    # Mount routes from all modules
    Mount("/auth", routes=auth_routes),
    Mount("/dashboard", routes=dashboard_routes),
    Mount("/users", routes=users_routes),
    # Mount other routes as they're created

    # Mount for hierarchical URL structure (company/site)
    # These will be processed by the ContextMiddleware
    Route("/company-{company_id:str}", endpoint=homepage),
    Route("/company-{company_id:str}/dashboard",
          endpoint=lambda request: RedirectResponse("/company-" + request.path_params["company_id"] + "/dashboard/")),
    Route("/company-{company_id:str}/dashboard/", endpoint=lambda request: RedirectResponse("/dashboard/")),

    # Direct site routes without company
    Route("/site-{site_id:str}", endpoint=homepage),
    Route("/site-{site_id:str}/dashboard",
          endpoint=lambda request: RedirectResponse("/site-" + request.path_params["site_id"] + "/dashboard/")),
    Route("/site-{site_id:str}/dashboard/", endpoint=lambda request: RedirectResponse("/dashboard/")),

    # Company + site routes
    Route("/company-{company_id:str}/site-{site_id:str}", endpoint=homepage),
    Route("/company-{company_id:str}/site-{site_id:str}/dashboard", endpoint=lambda request: RedirectResponse(
        "/company-" + request.path_params["company_id"] + "/site-" + request.path_params["site_id"] + "/dashboard/")),
    Route("/company-{company_id:str}/site-{site_id:str}/dashboard/",
          endpoint=lambda request: RedirectResponse("/dashboard/")),
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
    context = {
        "request": request,
        "messages": [],
        "now": datetime.now(),
    }

    # Safely get messages from session if available
    if "session" in request.scope:
        context["messages"] = request.session.pop("messages", [])

    # Add user to context if available
    if "user" in request.scope:
        context["user"] = request.user

    # Add URL context
    if hasattr(request.state, "context"):
        context["url_context"] = request.state.context

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