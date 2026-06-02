class AuthError(Exception):
    """Base de las excepciones de dominio de autenticación."""


class EmailAlreadyExists(AuthError):
    """Se lanza cuando se intenta registrar un email ya existente."""


class InvalidCredentials(AuthError):
    """Se lanza cuando las credenciales de login son incorrectas o el email no existe."""
