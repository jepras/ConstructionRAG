"""Utilities for sanitizing filenames for storage systems."""

import re
import unicodedata
from pathlib import Path


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """Sanitize filename for Supabase storage compatibility.
    
    Args:
        filename: Original filename to sanitize
        max_length: Maximum allowed filename length (default: 200)
        
    Returns:
        Sanitized filename safe for storage
        
    Rules applied:
    - Convert to ASCII-compatible characters
    - Replace multiple consecutive underscores with single underscore
    - Replace problematic characters with safe alternatives
    - Preserve file extension
    - Ensure reasonable length limits
    """
    if not filename:
        return "unnamed_file"
    
    # Split into name and extension
    path = Path(filename)
    name = path.stem
    ext = path.suffix
    
    # Normalize unicode characters to ASCII equivalents where possible
    name = unicodedata.normalize('NFKD', name)
    # Convert to ASCII, ignoring characters that can't be converted
    name = name.encode('ascii', 'ignore').decode('ascii')
    
    # Convert problematic characters to safe alternatives
    replacements = {
        # Multiple underscores/dashes to single underscore
        r'_{2,}': '_',
        r'-{2,}': '-', 
        # Spaces and special characters to underscore
        r'[\s]+': '_',
        r'[<>:"/\\|?*]': '_',
        # Remove or replace other problematic characters
        r'[\x00-\x1f\x7f-\x9f]': '',  # Control characters
        r'[^\w\-_.]': '_',  # Non-word characters (keep word chars, hyphens, underscores, dots)
    }
    
    for pattern, replacement in replacements.items():
        name = re.sub(pattern, replacement, name)
    
    # Clean up consecutive underscores/hyphens that might result from replacements
    name = re.sub(r'[_-]+', lambda m: '_' if '_' in m.group() else '-', name)
    
    # Remove leading/trailing underscores and hyphens
    name = name.strip('_-.')
    
    # Ensure we have a valid name
    if not name or name == '.' or name == '..':
        name = "file"
    
    # Reconstruct filename with extension
    sanitized = f"{name}{ext}"
    
    # Truncate if too long, preserving extension
    if len(sanitized) > max_length:
        max_name_length = max_length - len(ext) - 3  # Reserve space for extension + "..."
        if max_name_length > 0:
            name = name[:max_name_length]
            sanitized = f"{name}{ext}"
        else:
            # Extension is very long, just truncate everything
            sanitized = sanitized[:max_length]
    
    return sanitized


def sanitize_storage_path(path: str) -> str:
    """Sanitize individual path components in a storage path.
    
    Args:
        path: Storage path with forward slashes
        
    Returns:
        Storage path with sanitized filename component
    """
    if not path:
        return path
        
    # Split path and sanitize only the filename (last component)
    path_parts = path.split('/')
    if len(path_parts) > 0:
        # Sanitize only the last part (filename)
        path_parts[-1] = sanitize_filename(path_parts[-1])
    
    return '/'.join(path_parts)