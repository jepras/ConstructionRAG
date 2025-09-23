# backend/src/utils/validation.py
"""Validation utilities for unified storage migration."""

import re
from typing import Dict, Any


def validate_project_name(name: str) -> Dict[str, Any]:
    """Validate project name - allows user-friendly names that can be converted to valid slugs."""
    # Basic validation rules
    if not name.strip():
        return {"valid": False, "error": "Project name is required"}

    if len(name) < 3:
        return {"valid": False, "error": "Project name must be at least 3 characters"}

    if len(name) > 50:
        return {"valid": False, "error": "Project name must be less than 50 characters"}

    # Allow letters, numbers, spaces, hyphens, underscores, and periods
    # These can all be converted to valid slugs
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\s\-_.]*[a-zA-Z0-9]$', name.strip()):
        return {
            "valid": False,
            "error": "Project name can only contain letters, numbers, spaces, hyphens, underscores, and periods. Must start and end with letter or number."
        }

    # Generate slug to check if it results in a valid name
    slug = generate_project_slug(name)
    if not slug or len(slug) < 2:
        return {
            "valid": False,
            "error": "Project name must result in a valid project identifier"
        }

    # Reserved names (check against slug)
    reserved = ['api', 'admin', 'www', 'mail', 'ftp', 'localhost', 'anonymous']
    if slug.lower() in reserved:
        return {"valid": False, "error": "This project name is reserved"}

    return {"valid": True}


def generate_project_slug(name: str) -> str:
    """Generate project slug from project name."""
    return (name.lower()
            .replace(' ', '-')
            .replace('_', '-')
            .replace('.', '-')
            .strip('-'))