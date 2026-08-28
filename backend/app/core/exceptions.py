class LabGeniusException(Exception):
    """Base exception for LabGenius."""
    pass


class DuplicateResourceException(LabGeniusException):
    pass


class ResourceNotFoundException(LabGeniusException):
    pass


class ValidationException(LabGeniusException):
    pass


class SecurityConflictException(LabGeniusException):
    pass
