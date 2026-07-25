"""Custom exception classes for centralized error handling.

These exceptions represent domain and infrastructure failures in a consistent
way so controllers and services can raise them without handling HTTP details.
"""


class AppException(Exception):
    """Base class for application-specific exceptions."""

    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValidationException(AppException):
    """Raised when request data is invalid."""

    def __init__(self, message):
        super().__init__(message, status_code=400)


class AuthenticationException(AppException):
    """Raised when authentication fails."""

    def __init__(self, message):
        super().__init__(message, status_code=401)


class AuthorizationException(AppException):
    """Raised when a user is not allowed to access a resource."""

    def __init__(self, message):
        super().__init__(message, status_code=403)


class ResourceNotFoundException(AppException):
    """Raised when a requested resource cannot be found."""

    def __init__(self, message):
        super().__init__(message, status_code=404)


class DatabaseException(AppException):
    """Raised when a repository operation fails."""

    def __init__(self, message):
        super().__init__(message, status_code=500)


class BusinessLogicException(AppException):
    """Raised when a business rule is violated."""

    def __init__(self, message):
        super().__init__(message, status_code=400)
