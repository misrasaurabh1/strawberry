import importlib
from functools import lru_cache
from typing import Optional


def import_module_symbol(
    selector: str, default_symbol_name: Optional[str] = None
) -> object:
    if ":" in selector:
        module_name, symbol_name = selector.split(":", 1)
    elif default_symbol_name:
        module_name, symbol_name = selector, default_symbol_name
    else:
        raise ValueError("Selector does not include a symbol name")

    # Key for symbol cache is (module_name, symbol_name)
    cache_key = (module_name, symbol_name)
    if cache_key in _symbol_cache:
        return _symbol_cache[cache_key]

    module = _cached_import_module(module_name)
    symbol = module

    # Fast lookup for single-symbol attribute (common case)
    if "." not in symbol_name:
        result = getattr(symbol, symbol_name)
        _symbol_cache[cache_key] = result
        return result

    # For dotted symbol names, split and traverse
    for attribute_name in symbol_name.split("."):
        symbol = getattr(symbol, attribute_name)

    _symbol_cache[cache_key] = symbol
    return symbol


# LRU cache for module imports to avoid repeated slow imports
@lru_cache(maxsize=128)
def _cached_import_module(module_name: str):
    return importlib.import_module(module_name)


__all__ = ["import_module_symbol"]

_symbol_cache = {}
