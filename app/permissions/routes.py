# app/permissions/routes.py
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.authentication import requires
from pathlib import Path

import httpx
from app.api.permissions_client import get_permissions_client
from app.dependencies import permission_required

# Get base directory path (project root)
BASE_DIR = Path(__file__).parent.parent.parent

# Initialize templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@requires(["authenticated"])
@permission_required(["view_permissions"])
async def permissions_list(request: Request):
    """
    Render permissions list page
    """
    # Get API client
    permissions_client = get_permissions_client(request)

    try:
        # Get query parameters
        params = dict(request.query_params)
        module = params.get("module")

        # Fetch permissions from API
        permissions = await permissions_client.get_permissions(module=module)

        # Get all modules for filter dropdown
        modules = await permissions_client.get_modules()

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "permissions/list.html",
            {
                "request": request,
                "messages": messages,
                "permissions": permissions,
                "modules": modules,
                "selected_module": module,
                "title": "Permissions"
            }
        )

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to view permissions"}
            ]
            return RedirectResponse(url="/dashboard", status_code=302)

        # Handle other API errors
        request.session["messages"] = [
            {"type": "error", "text": f"Error loading permissions: {str(e)}"}
        ]
        return RedirectResponse(url="/dashboard", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/dashboard", status_code=302)


@requires(["authenticated"])
@permission_required(["view_permissions"])
async def permission_detail(request: Request):
    """
    Render permission detail page
    """
    # Get permission ID from path parameters
    permission_id = request.path_params.get("permission_id")

    # Get API client
    permissions_client = get_permissions_client(request)

    try:
        # Fetch permission from API
        permission = await permissions_client.get_permission(permission_id)

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "permissions/detail.html",
            {
                "request": request,
                "messages": messages,
                "permission": permission,
                "title": f"Permission: {permission.get('name', '')}"
            }
        )

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 404:
            # Permission not found
            request.session["messages"] = [
                {"type": "error", "text": "Permission not found"}
            ]
        elif e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to view this permission"}
            ]
        else:
            # Handle other API errors
            request.session["messages"] = [
                {"type": "error", "text": f"Error loading permission: {str(e)}"}
            ]

        return RedirectResponse(url="/permissions", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/permissions", status_code=302)


@requires(["authenticated"])
@permission_required(["manage_permissions"])
async def permission_create_page(request: Request):
    """
    Render permission create page
    """
    # Get permissions client
    permissions_client = get_permissions_client(request)

    try:
        # Get modules for dropdown
        modules = await permissions_client.get_modules()

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "permissions/create.html",
            {
                "request": request,
                "messages": messages,
                "modules": modules,
                "title": "Create Permission"
            }
        )
    except Exception as e:
        # Handle exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"Error loading modules: {str(e)}"}
        ]
        return RedirectResponse(url="/permissions", status_code=302)


@requires(["authenticated"])
@permission_required(["manage_permissions"])
async def permission_create(request: Request):
    """
    Handle permission create form submission
    """
    # Get API client
    permissions_client = get_permissions_client(request)

    try:
        # Get form data
        form_data = await request.form()
        permission_data = {
            "code": form_data.get("code"),
            "name": form_data.get("name"),
            "module": form_data.get("module"),
            "description": form_data.get("description")
        }

        # Create permission through API
        permission = await permissions_client.create_permission(permission_data)

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"Permission {permission['name']} created successfully"}
        ]

        # Redirect to permissions list
        return RedirectResponse(url="/permissions", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error creating permission"

        # Try to extract error message from response
        try:
            error_data = await e.response.json()
            error_msg = error_data.get("detail", error_msg)
        except Exception:
            pass

            # app/permissions/routes.py (continued)
            request.session["messages"] = [
                {"type": "error", "text": error_msg}
            ]

            # Redirect back to create page
            return RedirectResponse(url="/permissions/create", status_code=302)

        except Exception as e:
            # Handle general exceptions
            request.session["messages"] = [
                {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
            ]
            return RedirectResponse(url="/permissions/create", status_code=302)

@requires(["authenticated"])
@permission_required(["manage_permissions"])
async def permission_edit_page(request: Request):
    """
    Render permission edit page
    """
    # Get permission ID from path parameters
    permission_id = request.path_params.get("permission_id")

    # Get API client
    permissions_client = get_permissions_client(request)

    try:
        # Fetch permission from API
        permission = await permissions_client.get_permission(permission_id)

        # Get modules for dropdown
        modules = await permissions_client.get_modules()

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "permissions/edit.html",
            {
                "request": request,
                "messages": messages,
                "permission": permission,
                "modules": modules,
                "title": f"Edit Permission: {permission.get('name', '')}"
            }
        )

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 404:
            # Permission not found
            request.session["messages"] = [
                {"type": "error", "text": "Permission not found"}
            ]
        elif e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to edit this permission"}
            ]
        else:
            # Handle other API errors
            request.session["messages"] = [
                {"type": "error", "text": f"Error loading permission: {str(e)}"}
            ]

        return RedirectResponse(url="/permissions", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/permissions", status_code=302)

@requires(["authenticated"])
@permission_required(["manage_permissions"])
async def permission_edit(request: Request):
    """
    Handle permission edit form submission
    """
    # Get permission ID from path parameters
    permission_id = request.path_params.get("permission_id")

    # Get API client
    permissions_client = get_permissions_client(request)

    try:
        # Get form data
        form_data = await request.form()
        permission_data = {
            "name": form_data.get("name"),
            "description": form_data.get("description")
        }

        # Update permission through API
        permission = await permissions_client.update_permission(permission_id, permission_data)

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"Permission {permission['name']} updated successfully"}
        ]

        # Redirect to permissions list
        return RedirectResponse(url="/permissions", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error updating permission"

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
        return RedirectResponse(url=f"/permissions/{permission_id}/edit", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url=f"/permissions/{permission_id}/edit", status_code=302)

@requires(["authenticated"])
@permission_required(["manage_permissions"])
async def permission_delete(request: Request):
    """
    Handle permission delete
    """
    # Get permission ID from path parameters
    permission_id = request.path_params.get("permission_id")

    # Get API client
    permissions_client = get_permissions_client(request)

    try:
        # Delete permission through API
        permission = await permissions_client.delete_permission(permission_id)

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"Permission {permission['name']} deleted successfully"}
        ]

        # If HTMX request, return success message as JSON
        if request.headers.get("HX-Request") == "true":
            return JSONResponse(
                {"success": True, "message": f"Permission {permission['name']} deleted successfully"})

        # Redirect to permissions list
        return RedirectResponse(url="/permissions", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error deleting permission"

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

        # Redirect to permissions list
        return RedirectResponse(url="/permissions", status_code=302)

    except Exception as e:
        # Handle general exceptions
        error_msg = f"An unexpected error occurred: {str(e)}"

        # If HTMX request, return error message as JSON
        if request.headers.get("HX-Request") == "true":
            return JSONResponse({"success": False, "message": error_msg}, status_code=500)

        request.session["messages"] = [
            {"type": "error", "text": error_msg}
        ]
        return RedirectResponse(url="/permissions", status_code=302)

@requires(["authenticated"])
@permission_required(["manage_permissions"])
async def initialize_permissions(request: Request):
    """
    Handle permission initialization from registry
    """
    # Get API client
    permissions_client = get_permissions_client(request)

    try:
        # Initialize permissions through API
        result = await permissions_client.initialize_permissions()

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": result.get("message", "Permissions initialized successfully")}
        ]

        # Redirect to permissions list
        return RedirectResponse(url="/permissions", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error initializing permissions"

        # Try to extract error message from response
        try:
            error_data = await e.response.json()
            error_msg = error_data.get("detail", error_msg)
        except Exception:
            pass

        request.session["messages"] = [
            {"type": "error", "text": error_msg}
        ]

        # Redirect to permissions list
        return RedirectResponse(url="/permissions", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/permissions", status_code=302)

    # Define routes
routes = [
    Route("/", endpoint=permissions_list, methods=["GET"]),
    Route("/create", endpoint=permission_create_page, methods=["GET"]),
    Route("/create", endpoint=permission_create, methods=["POST"]),
    Route("/{permission_id:uuid}", endpoint=permission_detail, methods=["GET"]),
    Route("/{permission_id:uuid}/edit", endpoint=permission_edit_page, methods=["GET"]),
    Route("/{permission_id:uuid}/edit", endpoint=permission_edit, methods=["POST"]),
    Route("/{permission_id:uuid}/delete", endpoint=permission_delete, methods=["POST", "DELETE"]),
    Route("/initialize", endpoint=initialize_permissions, methods=["POST"]),
]