import secrets


def generate_token() -> str:
    """Genera un token opaco URL-safe de 256 bits de entropía."""
    return secrets.token_urlsafe(32)
