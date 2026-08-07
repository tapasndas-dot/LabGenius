"""
Security configuration for LabGenius.

This module will hold security-related constants and
configuration used across authentication and authorization.
"""

ACCESS_TOKEN_EXPIRE_MINUTES = 30

PASSWORD_MIN_LENGTH = 8

MAX_LOGIN_ATTEMPTS = 5

ACCOUNT_LOCK_MINUTES = 30