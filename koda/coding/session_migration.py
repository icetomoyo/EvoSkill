"""
Session Version Migration
Equivalent to Pi Mono's packages/coding-agent/src/core/session-manager.ts migration

Migrates old session formats to current version.
"""
from typing import List, Dict, Any, Callable
from .session_entries import SessionEntry, entry_from_dict


# Current session version
CURRENT_SESSION_VERSION = 1


# Migration functions registry
_migrations: Dict[int, Callable[[List[Dict]], List[Dict]]] = {}


def register_migration(from_version: int, func: Callable[[List[Dict]], List[Dict]]):
    """Register a migration function"""
    _migrations[from_version] = func


def migrate_session_entries(entries: List[Dict], from_version: int) -> List[SessionEntry]:
    """
    Migrate session entries from old version to current.
    
    Args:
        entries: Raw entry dictionaries from old format
        from_version: Version of the entries
        
    Returns:
        List of migrated SessionEntry objects
    """
    if from_version >= CURRENT_SESSION_VERSION:
        # No migration needed
        return [entry_from_dict(e) for e in entries]
    
    # Apply migrations sequentially
    current_entries = entries
    for version in range(from_version, CURRENT_SESSION_VERSION):
        if version in _migrations:
            current_entries = _migrations[version](current_entries)
    
    # Convert to SessionEntry objects
    return [entry_from_dict(e) for e in current_entries]


def detect_version(data: Any) -> int:
    """
    Detect session version from data.
    
    Args:
        data: Session data (dict or list)
        
    Returns:
        Detected version number
    """
    if isinstance(data, dict):
        # Check for version field
        if "version" in data:
            return data["version"]
        if "entries" in data and isinstance(data["entries"], list):
            # Modern format without version - assume current
            return CURRENT_SESSION_VERSION
    
    # Legacy format (list of entries)
    return 0


# Migration from version 0 to 1
def _migrate_v0_to_v1(entries: List[Dict]) -> List[Dict]:
    """
    Migrate from version 0 (legacy) to version 1.
    
    Changes:
    - Add entry IDs if missing
    - Add entry type field if missing
    - Normalize timestamp format
    """
    migrated = []
    for i, entry in enumerate(entries):
        new_entry = dict(entry)
        
        # Add ID if missing
        if "id" not in new_entry:
            new_entry["id"] = f"entry_{i}"
        
        # Add type if missing (infer from content)
        if "type" not in new_entry:
            if "role" in new_entry:
                new_entry["type"] = "message"
            elif "operation" in new_entry:
                new_entry["type"] = "file"
            else:
                new_entry["type"] = "custom"
        
        # Normalize timestamp (ensure milliseconds)
        if "timestamp" in new_entry:
            ts = new_entry["timestamp"]
            if ts < 10000000000:  # If seconds, convert to milliseconds
                new_entry["timestamp"] = int(ts * 1000)
        else:
            from datetime import datetime
            new_entry["timestamp"] = int(datetime.now().timestamp() * 1000)
        
        # Add branch if missing
        if "branch" not in new_entry:
            new_entry["branch"] = "main"
        
        migrated.append(new_entry)
    
    return migrated


# Register migrations
register_migration(0, _migrate_v0_to_v1)


class MigrationError(Exception):
    """Error during session migration"""
    pass


def migrate_session_file(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate entire session file to current version.
    
    Args:
        data: Session file data
        
    Returns:
        Migrated session data
    """
    version = detect_version(data)
    
    if version >= CURRENT_SESSION_VERSION:
        return data
    
    if isinstance(data, list):
        # Legacy format - wrap it
        data = {"entries": data, "version": 0}
    
    if "entries" not in data:
        raise MigrationError("Session data missing 'entries' field")
    
    entries = data["entries"]
    migrated_entries = migrate_session_entries(entries, version)
    
    # Update data
    data["entries"] = [e.__dict__ for e in migrated_entries]
    data["version"] = CURRENT_SESSION_VERSION
    
    return data
