# backend/src/constants.py
"""Constants for unified storage migration."""

# Anonymous user constants for unified storage pattern
ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"
ANONYMOUS_USERNAME = "anonymous"

# Visibility levels for unified access control
class VisibilityLevel:
    PUBLIC = "public"
    PRIVATE = "private"
    INTERNAL = "internal"

# Valid visibility levels list
VALID_VISIBILITY_LEVELS = [
    VisibilityLevel.PUBLIC,
    VisibilityLevel.PRIVATE,
    VisibilityLevel.INTERNAL
]