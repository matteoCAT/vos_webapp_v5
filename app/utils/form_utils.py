from typing import Dict, Any, Union, List
from urllib.parse import parse_qsl


def parse_form_data(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse form data into a dictionary, handling multi-value fields

    Args:
        form_data: Raw form data

    Returns:
        Parsed form data dictionary
    """
    result = {}

    for key, value in form_data.items():
        # Handle checkbox values
        if key.endswith('[]'):
            base_key = key[:-2]
            if base_key not in result:
                result[base_key] = []
            result[base_key].append(value)
        else:
            result[key] = value

    return result


def parse_query_string(query_string: str) -> Dict[str, Union[str, List[str]]]:
    """
    Parse a query string into a dictionary

    Args:
        query_string: URL query string

    Returns:
        Parsed query parameters
    """
    if not query_string:
        return {}

    # Remove leading '?' if present
    if query_string.startswith('?'):
        query_string = query_string[1:]

    # Parse query string
    params = parse_qsl(query_string)

    # Group parameters
    result = {}
    for key, value in params:
        if key in result:
            if isinstance(result[key], list):
                result[key].append(value)
            else:
                result[key] = [result[key], value]
        else:
            result[key] = value

    return result