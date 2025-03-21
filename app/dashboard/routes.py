from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from pathlib import Path

from app.api_client import get_api_client

# Get base directory path (project root)
BASE_DIR = Path(__file__).parent.parent.parent

# Initialize templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")


async def dashboard(request: Request):
    """
    Render dashboard page with overview
    """
    # Check authentication - redirect to login if not authenticated
    if "user" not in request.scope or not request.user.is_authenticated:
        # Add error message to session
        if "session" in request.scope:
            request.session["messages"] = [
                {"type": "warning", "text": "Please login to access the dashboard"}
            ]
        return RedirectResponse(url="/auth/login", status_code=302)

    # Get API client
    api_client = get_api_client(request)

    try:
        # Fetch sites
        sites = await api_client.get_sites()

        # Here we would fetch various data for the dashboard
        # For now, we'll just fetch some basic data

        # Example: Get recent orders
        # recent_orders = await api_client.get("/orders?limit=5")
        recent_orders = []  # Placeholder

        # Example: Get inventory status
        # inventory_status = await api_client.get("/inventory/status")
        inventory_status = []  # Placeholder

        # Example: Get sales summary
        # sales_summary = await api_client.get("/sales/summary")
        sales_summary = {
            "today": {"total": 2580, "change": 12},
            "active_orders": 16,
            "reservations": 8
        }  # Placeholder

        # Get any messages from session
        messages = request.session.pop("messages", []) if "session" in request.scope else []

        return templates.TemplateResponse(
            "dashboard/index.html",
            {
                "request": request,
                "user": request.scope["user"],
                "messages": messages,
                "recent_orders": recent_orders,
                "inventory_status": inventory_status,
                "sales_summary": sales_summary,
                "sites": sites  # Pass sites to the template
            }
        )

    except Exception as e:
        # Add error message to session
        if "session" in request.scope:
            request.session["messages"] = [
                {"type": "error", "text": f"Error loading dashboard: {str(e)}"}
            ]

        # Since this is the dashboard, if we can't load it, redirect to login
        # as there might be an authentication issue
        return RedirectResponse(url="/auth/login", status_code=302)


# Define routes
routes = [
    Route("/", endpoint=dashboard, methods=["GET"]),
]