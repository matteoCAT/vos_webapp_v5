from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.authentication import requires

import httpx
from app.api_client import get_api_client

# Initialize templates
templates = Jinja2Templates(directory="templates")


@requires(["authenticated"])
async def users_list(request: Request):
    """
    Render users list page
    """
    # Get API client
    api_client = get_api_client(request)

    try:
        # Get query parameters
        params = dict(request.query_params)
        page = int(params.get("page", 1))
        limit = int(params.get("limit", 10))

        # Calculate offset for pagination
        offset = (page - 1) * limit

        # Fetch users from API
        users = await api_client.get("/users", params={"skip": offset, "limit": limit})

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "users/list.html",
            {
                "request": request,
                "messages": messages,
                "users": users,
                "page": page,
                "limit": limit,
                "total": len(users),  # This would be replaced with a total count from the API
                "title": "Users"
            }
        )

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to view users"}
            ]
            return RedirectResponse(url="/dashboard", status_code=302)

        # Handle other API errors
        request.session["messages"] = [
            {"type": "error", "text": f"Error loading users: {str(e)}"}
        ]
        return RedirectResponse(url="/dashboard", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/dashboard", status_code=302)


@requires(["authenticated"])
async def user_detail(request: Request):
    """
    Render user detail page
    """
    # Get user ID from path parameters
    user_id = request.path_params.get("user_id")

    # Get API client
    api_client = get_api_client(request)

    try:
        # Fetch user from API
        user = await api_client.get(f"/users/{user_id}")

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "users/detail.html",
            {
                "request": request,
                "messages": messages,
                "user": user,
                "title": f"User: {user.get('username', '')}"
            }
        )

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 404:
            # User not found
            request.session["messages"] = [
                {"type": "error", "text": "User not found"}
            ]
        elif e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to view this user"}
            ]
        else:
            # Handle other API errors
            request.session["messages"] = [
                {"type": "error", "text": f"Error loading user: {str(e)}"}
            ]

        return RedirectResponse(url="/users", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/users", status_code=302)


@requires(["authenticated"])
async def user_create_page(request: Request):
    """
    Render user create page
    """
    # Get any messages from session
    messages = request.session.pop("messages", [])

    return templates.TemplateResponse(
        "users/create.html",
        {
            "request": request,
            "messages": messages,
            "title": "Create User"
        }
    )


@requires(["authenticated"])
async def user_create(request: Request):
    """
    Handle user create form submission
    """
    # Get API client
    api_client = get_api_client(request)

    try:
        # Get form data
        form_data = await request.form()
        user_data = {
            "email": form_data.get("email"),
            "username": form_data.get("username"),
            "name": form_data.get("name"),
            "surname": form_data.get("surname"),
            "telephone": form_data.get("telephone", ""),
            "password": form_data.get("password"),
            "role": form_data.get("role", "staff"),
            "is_active": form_data.get("is_active") == "on"
        }

        # Create user through API
        user = await api_client.post("/users", json_data=user_data)

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"User {user['username']} created successfully"}
        ]

        # Redirect to users list
        return RedirectResponse(url="/users", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error creating user"

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
        return RedirectResponse(url="/users/create", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/users/create", status_code=302)


@requires(["authenticated"])
async def user_edit_page(request: Request):
    """
    Render user edit page
    """
    # Get user ID from path parameters
    user_id = request.path_params.get("user_id")

    # Get API client
    api_client = get_api_client(request)

    try:
        # Fetch user from API
        user = await api_client.get(f"/users/{user_id}")

        # Get any messages from session
        messages = request.session.pop("messages", [])

        return templates.TemplateResponse(
            "users/edit.html",
            {
                "request": request,
                "messages": messages,
                "user": user,
                "title": f"Edit User: {user.get('username', '')}"
            }
        )

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        if e.response.status_code == 404:
            # User not found
            request.session["messages"] = [
                {"type": "error", "text": "User not found"}
            ]
        elif e.response.status_code == 403:
            # User doesn't have permission
            request.session["messages"] = [
                {"type": "error", "text": "You don't have permission to edit this user"}
            ]
        else:
            # Handle other API errors
            request.session["messages"] = [
                {"type": "error", "text": f"Error loading user: {str(e)}"}
            ]

        return RedirectResponse(url="/users", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url="/users", status_code=302)


@requires(["authenticated"])
async def user_edit(request: Request):
    """
    Handle user edit form submission
    """
    # Get user ID from path parameters
    user_id = request.path_params.get("user_id")

    # Get API client
    api_client = get_api_client(request)

    try:
        # Get form data
        form_data = await request.form()
        user_data = {
            "email": form_data.get("email"),
            "username": form_data.get("username"),
            "name": form_data.get("name"),
            "surname": form_data.get("surname"),
            "telephone": form_data.get("telephone", ""),
            "role": form_data.get("role", "staff"),
            "is_active": form_data.get("is_active") == "on"
        }

        # Only include password if it's provided
        password = form_data.get("password")
        if password:
            user_data["password"] = password

        # Update user through API
        user = await api_client.put(f"/users/{user_id}", json_data=user_data)

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"User {user['username']} updated successfully"}
        ]

        # Redirect to users list
        return RedirectResponse(url="/users", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error updating user"

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
        return RedirectResponse(url=f"/users/{user_id}/edit", status_code=302)

    except Exception as e:
        # Handle general exceptions
        request.session["messages"] = [
            {"type": "error", "text": f"An unexpected error occurred: {str(e)}"}
        ]
        return RedirectResponse(url=f"/users/{user_id}/edit", status_code=302)


@requires(["authenticated"])
async def user_delete(request: Request):
    """
    Handle user delete
    """
    # Get user ID from path parameters
    user_id = request.path_params.get("user_id")

    # Get API client
    api_client = get_api_client(request)

    try:
        # Delete user through API
        user = await api_client.delete(f"/users/{user_id}")

        # Add success message
        request.session["messages"] = [
            {"type": "success", "text": f"User {user['username']} deleted successfully"}
        ]

        # If HTMX request, return success message as JSON
        if request.headers.get("HX-Request") == "true":
            return JSONResponse({"success": True, "message": f"User {user['username']} deleted successfully"})

        # Redirect to users list
        return RedirectResponse(url="/users", status_code=302)

    except httpx.HTTPStatusError as e:
        # Handle API HTTP errors
        error_msg = "Error deleting user"

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

        # Redirect to users list
        return RedirectResponse(url="/users", status_code=302)

    except Exception as e:
        # Handle general exceptions
        error_msg = f"An unexpected error occurred: {str(e)}"

        # If HTMX request, return error message as JSON
        if request.headers.get("HX-Request") == "true":
            return JSONResponse({"success": False, "message": error_msg}, status_code=500)

        request.session["messages"] = [
            {"type": "error", "text": error_msg}
        ]
        return RedirectResponse(url="/users", status_code=302)


# Define routes
routes = [
    Route("/", endpoint=users_list, methods=["GET"]),
    Route("/create", endpoint=user_create_page, methods=["GET"]),
    Route("/create", endpoint=user_create, methods=["POST"]),
    Route("/{user_id:uuid}", endpoint=user_detail, methods=["GET"]),
    Route("/{user_id:uuid}/edit", endpoint=user_edit_page, methods=["GET"]),
    Route("/{user_id:uuid}/edit", endpoint=user_edit, methods=["POST"]),
    Route("/{user_id:uuid}/delete", endpoint=user_delete, methods=["POST", "DELETE"]),
]