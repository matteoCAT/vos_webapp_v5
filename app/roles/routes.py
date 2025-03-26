# app/roles/routes.py
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.authentication import requires
from pathlib import Path

import httpx
from app.api.roles_client import get_roles_client
from app.api.permissions_client import get_permissions_client
from app.dependencies import permission_required

# Get base directory path (project root)
BASE_DIR = Path(__file__).parent.parent.parent

# Initialize templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@requires(["authenticated"])
@permission_required(["view_roles"])
async def roles_list(request: Request):
    """
    Render roles list page
    """
    # Get API client
    roles_client = get_roles_client(request)

    try:
        # Fetch roles from API
        roles = await roles_client.get_roles()

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "roles/list.html",
            {
                "request": request,
                "messages": messages,
                "roles": roles,
                "title": "Roles"
            }
        )

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to view roles"}
            ]
            return RedirectResponse(url="/dashboard", status_code=302)

        # Handle other API errors
        request.session["messages"] = [
            {"type": "error", "text": f"Error loading roles: {str(e)}"}
        ]
        return RedirectResponse(url="/dashboard", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/dashboard", status_code=302)


@requires(["authenticated"])
@permission_required(["view_roles"])
async def role_detail(request: Request):
    """
    Render role detail page
    """
    # Get role ID from path parameters
    role_id = request.path_params.get("role_id")

    # Get API client
    roles_client = get_roles_client(request)

    try:
        # Fetch role from API
        role = await roles_client.get_role(role_id)

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "roles/detail.html",
            {
                "request": request,
                "messages": messages,
                "role": role,
                "title": f"Role: {role.get('name', '')}"
            }
        )

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 404:
            # Role not found
            request.session["messages"] = [
                {"type": "error", "text": "Role not found"}
            ]
        elif e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to view this role"}
            ]
        else:
            # Handle other API errors
            request.session["messages"] = [
                {"type": "error", "text": f"Error loading role: {str(e)}"}
            ]

        return RedirectResponse(url="/roles", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/roles", status_code=302)


@requires(["authenticated"])
@permission_required(["manage_roles"])
async def role_create_page(request: Request):
    """
    Render role create page
    """
    # Get permissions client to fetch available permissions
    permissions_client = get_permissions_client(request)

    try:
        # Fetch permissions from API
        permissions = await permissions_client.get_permissions()
        modules = await permissions_client.get_modules()

        # Group permissions by module
        permissions_by_module = {}
        for module in modules:
            permissions_by_module[module] = [p for p in permissions if p.get("module") == module]

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "roles/create.html",
            {
                "request": request,
                "messages": messages,
                "permissions": permissions,
                "permissions_by_module": permissions_by_module,
                "title": "Create Role"
            }
        )
    except Exception as e:
        # Handle exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"Error loading permissions: {str(e)}"}
        ]
        return RedirectResponse(url="/roles", status_code=302)


@requires(["authenticated"])
@permission_required(["manage_roles"])
async def role_create(request: Request):
    """
    Handle role create form submission
    """
    # Get API client
    roles_client = get_roles_client(request)

    try:
        # Get form data
        form_data = await request.form()

        # Extract permission IDs (multi-select checkboxes)
        permission_ids = []
        for key, value in form_data.items():
            if key.startswith('permission_') and value == 'on':
                permission_id = key.replace('permission_', '')
                permission_ids.append(permission_id)
        role_data = {
            "name": form_data.get("name"),
            "description": form_data.get("description"),
            "is_system_role": form_data.get("is_system_role") == "on",
            "permission_ids": permission_ids
        }
        # Create role through API
        role = await roles_client.create_role(role_data)
        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"Role {role['name']} created successfully"}
        ]
        # Redirect to roles list
        return RedirectResponse(url="/roles", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error creating role"
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
        return RedirectResponse(url="/roles/create", status_code=302)


    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]

        return RedirectResponse(url="/roles/create", status_code=302)


@requires(["authenticated"])
@permission_required(["manage_roles"])
async def role_edit_page(request: Request):
    """
    Render role edit page
    """
    # Get role ID from path parameters
    role_id = request.path_params.get("role_id")

    # Get API clients
    roles_client = get_roles_client(request)
    permissions_client = get_permissions_client(request)

    try:
        # Fetch role from API
        role = await roles_client.get_role(role_id)
        # Fetch all permissions
        permissions = await permissions_client.get_permissions()
        modules = await permissions_client.get_modules()
        # Get role's permissions IDs for pre-selecting checkboxes
        role_permission_ids = [p.get("id") for p in role.get("permissions", [])]
        # Group permissions by module
        permissions_by_module = {}
        for module in modules:
            permissions_by_module[module] = [p for p in permissions if p.get("module") == module]

        # Get any messages from session
        messages = request.session.pop("messages", [])
        return templates.TemplateResponse(
            "roles/edit.html",
            {
                "request": request,
                "messages": messages,
                "role": role,
                "permissions": permissions,
                "permissions_by_module": permissions_by_module,
                "role_permission_ids": role_permission_ids,
                "title": f"Edit Role: {role.get('name', '')}"
            }
        )


    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 404:
            # Role not found
            request.session["messages"] = [
                {"type": "error", "text": "Role not found"}
            ]

        elif e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to edit this role"}
            ]
        else:
            # Handle other API errors
            request.session["messages"] = [
                {"type": "error", "text": f"Error loading role: {str(e)}"}
            ]
        return RedirectResponse(url="/roles", status_code=302)


    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/roles", status_code=302)


@requires(["authenticated"])
@permission_required(["manage_roles"])
async def role_edit(request: Request):
    """
    Handle role edit form submission
    """
    # Get role ID from path parameters
    role_id = request.path_params.get("role_id")
    # Get API clients
    roles_client = get_roles_client(request)
    permissions_client = get_permissions_client(request)

    try:
        # Get form data
        form_data = await request.form()
        # Basic role data
        role_data = {
            "name": form_data.get("name"),
            "description": form_data.get("description")
        }

        # Update basic role data
        role = await roles_client.update_role(role_id, role_data)
        # Handle permissions separately
        # Extract permission IDs (multi-select checkboxes)
        new_permission_ids = []
        for key, value in form_data.items():
            if key.startswith('permission_') and value == 'on':
                permission_id = key.replace('permission_', '')
                new_permission_ids.append(permission_id)

        # Get current role data to compare permissions
        current_role = await roles_client.get_role(role_id)
        current_permission_ids = [p.get("id") for p in current_role.get("permissions", [])]
        # Determine which permissions to add and which to remove
        permissions_to_add = [p_id for p_id in new_permission_ids if p_id not in current_permission_ids]
        permissions_to_remove = [p_id for p_id in current_permission_ids if p_id not in new_permission_ids]

        # Update permissions if needed
        if permissions_to_add or permissions_to_remove:
            await roles_client.update_role_permissions(
                role_id,
                add_permission_ids=permissions_to_add,
                remove_permission_ids=permissions_to_remove
            )
        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"Role {role['name']} updated successfully"}
        ]

        # Redirect to roles list
        return RedirectResponse(url="/roles", status_code=302)


    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error updating role"
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
        return RedirectResponse(url=f"/roles/{role_id}/edit", status_code=302)


    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]

        return RedirectResponse(url=f"/roles/{role_id}/edit", status_code=302)


@requires(["authenticated"])
@permission_required(["manage_roles"])
async def role_delete(request: Request):
    """
    Handle role delete
    """
    # Get role ID from path parameters
    role_id = request.path_params.get("role_id")
    # Get API client
    roles_client = get_roles_client(request)
    try:
        # Delete role through API
        role = await roles_client.delete_role(role_id)
        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"Role {role['name']} deleted successfully"}
        ]

        # If HTMX request, return success message as JSON
        if request.headers.get("HX-Request") == "true":
            return JSONResponse({"success": True, "message": f"Role {role['name']} deleted successfully"})

        # Redirect to roles list
        return RedirectResponse(url="/roles", status_code=302)


    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error deleting role"
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
        # Redirect to roles list
        return RedirectResponse(url="/roles", status_code=302)


    except Exception as e:
        # Handle general exceptions
        error_msg = f"An unexpected error occurred: {str(e)}"
        # If HTMX request, return error message as JSON
        if request.headers.get("HX-Request") == "true":
            return JSONResponse({"success": False, "message": error_msg}, status_code=500)
        request.session["messages"] = [
            {"type": "error", "text": error_msg}
        ]
        return RedirectResponse(url="/roles", status_code=302)

# Define routes
routes = [
    Route("/", endpoint=roles_list, methods=["GET"]),
    Route("/create", endpoint=role_create_page, methods=["GET"]),
    Route("/create", endpoint=role_create, methods=["POST"]),
    Route("/{role_id:uuid}", endpoint=role_detail, methods=["GET"]),
    Route("/{role_id:uuid}/edit", endpoint=role_edit_page, methods=["GET"]),
    Route("/{role_id:uuid}/edit", endpoint=role_edit, methods=["POST"]),
    Route("/{role_id:uuid}/delete", endpoint=role_delete, methods=["POST", "DELETE"]),
]