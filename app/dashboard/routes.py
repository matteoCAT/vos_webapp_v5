from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from pathlib import Path

from app.api.sites_client import get_sites_client

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
    # Get URL context
    context = getattr(request.state, "context", {})
    company_id = context.get("company_id")
    site_id = context.get("site_id")

    # Get sites client
    sites_client = get_sites_client(request)

    try:
        # Fetch sites for the dropdown
        sites = await sites_client.get_sites(company_id=company_id)

        # If we have a site_id, get specific site details
        current_site = None
        if site_id:
            try:
                current_site = await sites_client.get_site(site_id)
            except Exception as e:
                print(f"Error fetching site details: {e}")

        # Example dummy data that would come from API
        # In real implementation, this would be fetched from appropriate API endpoints
        recent_orders = []
        inventory_status = []
        sales_summary = {
            "today": {"total": 2580, "change": 12},
            "active_orders": 16,
            "reservations": 8
        }

        # Customize title based on context
        title = "Dashboard"
        if current_site:
            title = f"{current_site['name']} - Dashboard"
        elif company_id:
            title = f"Company Dashboard"

        # Prepare template context
        template_context = {
            "request": request,
            "user": request.user if "user" in request.scope else None,
            "title": title,
            "sites": sites,
            "current_site": current_site,
            "company_id": company_id,
            "site_id": site_id,
            "recent_orders": recent_orders,
            "inventory_status": inventory_status,
            "sales_summary": sales_summary,
            "messages": request.state.template_context.get("messages", []),
        }

        return templates.TemplateResponse("dashboard/index.html", template_context)

    except Exception as e:
        # Add error message to session
        if "session" in request.scope:
            request.session["messages"] = [
                {"type": "error", "text": f"Error loading dashboard: {str(e)}"}
            ]

        # Since there was an error, redirect to login
        return RedirectResponse(url="/auth/login", status_code=302)


# Define routes
routes = [
    Route("/", endpoint=dashboard, methods=["GET"]),
]