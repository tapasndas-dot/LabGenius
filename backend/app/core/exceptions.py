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


class VersionConflictException(LabGeniusException):
    """Raised when an expected-version business mutation is stale."""

    pass


class CapabilityConflictException(LabGeniusException):
    pass
