import copy
from collections.abc import Mapping
from typing import Any


def replace_placeholders_with_files(
    operations_with_placeholders: dict[str, Any],
    files_map: Mapping[str, Any],
    files: Mapping[str, Any],
) -> dict[str, Any]:
    # Only copy the structure that will be mutated.
    operations = _shallow_copy_structure(operations_with_placeholders)

    # For caching split paths if repeated (optional - comment out if unused)
    split_path_cache = {}

    for multipart_form_field_name, operations_paths in files_map.items():
        file_object = files[multipart_form_field_name]

        for path in operations_paths:
            if path in split_path_cache:
                operations_path_keys, value_key = split_path_cache[path]
            else:
                split_path = path.split(".")
                *operations_path_keys, value_key = split_path
                split_path_cache[path] = (operations_path_keys, value_key)

            # Traverse to just before the final value
            target_object = operations
            for key in operations_path_keys:
                # Check key type in advance to avoid repeated isinstance
                if isinstance(target_object, list):
                    idx = int(key)
                    if not isinstance(target_object[idx], (dict, list)):
                        target_object[idx] = target_object[idx].copy() if isinstance(target_object[idx], dict) else list(target_object[idx]) if isinstance(target_object[idx], list) else target_object[idx]
                    target_object = target_object[idx]
                else:
                    if not isinstance(target_object[key], (dict, list)):
                        target_object[key] = target_object[key].copy() if isinstance(target_object[key], dict) else list(target_object[key]) if isinstance(target_object[key], list) else target_object[key]
                    target_object = target_object[key]

            # Finally, set the file_object at the correct location.
            if isinstance(target_object, list):
                target_object[int(value_key)] = file_object
            else:
                target_object[value_key] = file_object

    return operations


def _shallow_copy_structure(obj):
    """Shallow copy lists and dicts in the outermost structure only."""
    if isinstance(obj, dict):
        return {k: _shallow_copy_structure(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_shallow_copy_structure(i) for i in obj]
    else:
        return obj


__all__ = ["replace_placeholders_with_files"]
