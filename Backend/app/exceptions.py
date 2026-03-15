class WrongItemIdError(Exception):
    pass


class AuthenticationError(Exception):
    """Invalid credentials."""


class AccountBlockedError(Exception):
    """Account is blocked."""


class InvalidTokenError(Exception):
    """Invalid or expired token."""
