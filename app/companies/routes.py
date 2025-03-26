# app/companies/routes.py
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.authentication import requires
from pathlib import Path

import httpx
from app.api.companies_client import get_companies_client
from app.dependencies import permission_required

# Get base directory path (project root)
BASE_DIR = Path(__file__).parent.parent.parent

# Initialize templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@requires(["authenticated"])
@permission_required(["view_companies"])
async def companies_list(request: Request):
    """
    Render companies list page
    """
    # Get API client
    companies_client = get_companies_client(request)

    try:
        # Get query parameters
        params = dict(request.query_params)
        active_only = params.get("active_only", "false").lower() in ("true", "1", "t")

        # Fetch companies from API
        companies = await companies_client.get_companies(active_only=active_only)

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "companies/list.html",
            {
                "request": request,
                "messages": messages,
                "companies": companies,
                "active_only": active_only,
                "title": "Companies"
            }
        )

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to view companies"}
            ]
            return RedirectResponse(url="/dashboard", status_code=302)

        # Handle other API errors
        request.session["messages"] = [
            {"type": "error", "text": f"Error loading companies: {str(e)}"}
        ]
        return RedirectResponse(url="/dashboard", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/dashboard", status_code=302)


@requires(["authenticated"])
@permission_required(["view_companies"])
async def company_detail(request: Request):
    """
    Render company detail page
    """
    # Get company ID from path parameters
    company_id = request.path_params.get("company_id")

    # Get API client
    companies_client = get_companies_client(request)

    try:
        # Fetch company from API
        company = await companies_client.get_company(company_id)

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "companies/detail.html",
            {
                "request": request,
                "messages": messages,
                "company": company,
                "title": f"Company: {company.get('name', '')}"
            }
        )

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 404:
            # Company not found
            request.session["messages"] = [
                {"type": "error", "text": "Company not found"}
            ]
        elif e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to view this company"}
            ]
        else:
            # Handle other API errors
            request.session["messages"] = [
                {"type": "error", "text": f"Error loading company: {str(e)}"}
            ]

        return RedirectResponse(url="/companies", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/companies", status_code=302)


@requires(["authenticated"])
@permission_required(["manage_companies"])
async def company_create_page(request: Request):
    """
    Render company create page
    """
    # Get any messages from session
    messages = request.session.pop("messages", [])

    return templates.TemplateResponse(
        "companies/create.html",
        {
            "request": request,
            "messages": messages,
            "title": "Create Company"
        }
    )


@requires(["authenticated"])
@permission_required(["manage_companies"])
async def company_create(request: Request):
    """
    Handle company create form submission
    """
    # Get API client
    companies_client = get_companies_client(request)

    try:
        # Get form data
        form_data = await request.form()
        company_data = {
            "name": form_data.get("name"),
            "slug": form_data.get("slug"),
            "display_name": form_data.get("display_name"),
            "description": form_data.get("description"),
            "contact_name": form_data.get("contact_name"),
            "email": form_data.get("email"),
            "phone": form_data.get("phone"),
            "address": form_data.get("address"),
            "tax_id": form_data.get("tax_id"),
            "registration_number": form_data.get("registration_number"),
            "is_active": form_data.get("is_active") == "on"
        }

        # Create company through API
        company = await companies_client.create_company(company_data)

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"Company {company['name']} created successfully"}
        ]

        # Redirect to companies list
        return RedirectResponse(url="/companies", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error creating company"

        # Try to extract error message from response
        try:
            error_data = await e.response.json()
            error_msg = error_data.get("detail", error_msg)
        except Exception:
            pass

        request.session["messages"] = [
            {"type": "error", "text": error_msg}
        ]

        # Redirect back to create page
        return RedirectResponse(url="/companies/create", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/companies/create", status_code=302)


# app/companies/routes.py (continued)
@requires(["authenticated"])
@permission_required(["manage_companies"])
async def company_edit_page(request: Request):
    """
    Render company edit page
    """
    # Get company ID from path parameters
    company_id = request.path_params.get("company_id")

    # Get API client
    companies_client = get_companies_client(request)

    try:
        # Fetch company from API
        company = await companies_client.get_company(company_id)

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "companies/edit.html",
            {
                "request": request,
                "messages": messages,
                "company": company,
                "title": f"Edit Company: {company.get('name', '')}"
            }
        )

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 404:
            # Company not found
            request.session["messages"] = [
                {"type": "error", "text": "Company not found"}
            ]
        elif e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to edit this company"}
            ]
        else:
            # Handle other API errors
            request.session["messages"] = [
                {"type": "error", "text": f"Error loading company: {str(e)}"}
            ]

        return RedirectResponse(url="/companies", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/companies", status_code=302)


@requires(["authenticated"])
@permission_required(["manage_companies"])
async def company_edit(request: Request):
    """
    Handle company edit form submission
    """
    # Get company ID from path parameters
    company_id = request.path_params.get("company_id")

    # Get API client
    companies_client = get_companies_client(request)

    try:
        # Get form data
        form_data = await request.form()
        company_data = {
            "name": form_data.get("name"),
            "slug": form_data.get("slug"),
            "display_name": form_data.get("display_name"),
            "description": form_data.get("description"),
            "contact_name": form_data.get("contact_name"),
            "email": form_data.get("email"),
            "phone": form_data.get("phone"),
            "address": form_data.get("address"),
            "tax_id": form_data.get("tax_id"),
            "registration_number": form_data.get("registration_number"),
            "is_active": form_data.get("is_active") == "on"
        }

        # Update company through API
        company = await companies_client.update_company(company_id, company_data)

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"Company {company['name']} updated successfully"}
        ]

        # Redirect to companies list
        return RedirectResponse(url="/companies", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error updating company"

        # Try to extract error message from response
        try:
            error_data = await e.response.json()
            error_msg = error_data.get("detail", error_msg)
        except Exception:
            pass

        request.session["messages"] = [
            {"type": "error", "text": error_msg}
        ]

        # Redirect back to edit page
        return RedirectResponse(url=f"/companies/{company_id}/edit", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url=f"/companies/{company_id}/edit", status_code=302)


@requires(["authenticated"])
@permission_required(["manage_companies"])
async def company_delete(request: Request):
    """
    Handle company delete
    """
    # Get company ID from path parameters
    company_id = request.path_params.get("company_id")

    # Get API client
    companies_client = get_companies_client(request)

    try:
        # Delete company through API
        company = await companies_client.delete_company(company_id)

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"Company {company['name']} deleted successfully"}
        ]

        # If HTMX request, return success message as JSON
        if request.headers.get("HX-Request") == "true":
            return JSONResponse({"success": True, "message": f"Company {company['name']} deleted successfully"})

        # Redirect to companies list
        return RedirectResponse(url="/companies", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error deleting company"

        # Try to extract error message from response
        try:
            error_data = await e.response.json()
            error_msg = error_data.get("detail", error_msg)
        except Exception:
            pass

        # If HTMX request, return error message as JSON
        if request.headers.get("HX-Request") == "true":
            return JSONResponse({"success": False, "message": error_msg}, status_code=e.response.status_code)

        request.session["messages"] = [
            {"type": "error", "text": error_msg}
        ]

        # Redirect to companies list
        return RedirectResponse(url="/companies", status_code=302)

    except Exception as e:
        # Handle general exceptions
        error_msg = f"An unexpected error occurred: {str(e)}"

        # If HTMX request, return error message as JSON
        if request.headers.get("HX-Request") == "true":
            return JSONResponse({"success": False, "message": error_msg}, status_code=500)

        request.session["messages"] = [
            {"type": "error", "text": error_msg}
        ]
        return RedirectResponse(url="/companies", status_code=302)


@requires(["authenticated"])
@permission_required(["manage_companies"])
async def company_drop_schema(request: Request):
    """
    Handle company schema drop
    """
    # Get company ID from path parameters
    company_id = request.path_params.get("company_id")

    # Get form data for confirmation
    form_data = await request.form()
    confirm = form_data.get("confirm") == "on"

    if not confirm:
        # Add error message if not confirmed
        request.session["messages"] = [
            {"type": "error", "text": "Schema deletion requires confirmation"}
        ]
        return RedirectResponse(url=f"/companies/{company_id}", status_code=302)

    # Get API client
    companies_client = get_companies_client(request)

    try:
        # Drop schema through API
        result = await companies_client.drop_schema(company_id)

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": result.get("message", "Schema dropped successfully")}
        ]

        # Redirect to companies list
        return RedirectResponse(url="/companies", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error dropping schema"

        # Try to extract error message from response
        try:
            error_data = await e.response.json()
            error_msg = error_data.get("detail", error_msg)
        except Exception:
            pass

        request.session["messages"] = [
            {"type": "error", "text": error_msg}
        ]

        # Redirect back to company detail page
        return RedirectResponse(url=f"/companies/{company_id}", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url=f"/companies/{company_id}", status_code=302)


# Define routes
routes = [
    Route("/", endpoint=companies_list, methods=["GET"]),
    Route("/create", endpoint=company_create_page, methods=["GET"]),
    Route("/create", endpoint=company_create, methods=["POST"]),
    Route("/{company_id:uuid}", endpoint=company_detail, methods=["GET"]),
    Route("/{company_id:uuid}/edit", endpoint=company_edit_page, methods=["GET"]),
    Route("/{company_id:uuid}/edit", endpoint=company_edit, methods=["POST"]),
    Route("/{company_id:uuid}/delete", endpoint=company_delete, methods=["POST", "DELETE"]),
    Route("/{company_id:uuid}/drop-schema", endpoint=company_drop_schema, methods=["POST"]),
]