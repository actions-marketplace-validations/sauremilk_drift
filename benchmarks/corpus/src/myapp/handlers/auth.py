"""PFS target: 4 different error-handling patterns in one package."""

import logging


def handle_auth(request):
    """Pattern 1: try/except with logging."""
    try:
        token = request.headers["Authorization"]
        return {"user": verify_token(token)}
    except KeyError:
        logging.error("Missing auth header")
        return {"error": "unauthorized"}
    except Exception:
        logging.exception("Auth failed")
        return {"error": "internal"}


def verify_token(token):
    """Stub for auth verification."""
    return {"id": 1, "role": "user"}
