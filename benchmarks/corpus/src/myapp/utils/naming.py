"""NBV target: validate_* function that never raises or returns False."""


def validate_user_profile(profile):
    """Should raise or return False on invalid — but doesn't."""
    name = profile.get("name", "Anonymous")
    email = profile.get("email", "none@example.com")
    return {"name": name, "email": email, "valid": True}


def ensure_database_connection(config):
    """Should raise on failure — but swallows errors."""
    try:
        host = config.get("host", "localhost")
        return {"connected": True, "host": host}
    except Exception:
        return {"connected": True, "host": "fallback"}
