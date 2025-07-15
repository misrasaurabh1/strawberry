import warnings

from .add_validation_rules import AddValidationRules
from .base_extension import LifecycleStep, SchemaExtension
from .disable_introspection import DisableIntrospection
from .disable_validation import DisableValidation
from .field_extension import FieldExtension
from .mask_errors import MaskErrors
from .max_aliases import MaxAliasesLimiter
from .max_tokens import MaxTokensLimiter
from .parser_cache import ParserCache
from .query_depth_limiter import IgnoreContext, QueryDepthLimiter
from .validation_cache import ValidationCache


def __getattr__(name: str) -> type[SchemaExtension]:
    global _warned_extension

    if name == "Extension":
        if not _warned_extension:
            warnings.warn(
                (
                    "importing `Extension` from `strawberry.extensions` "
                    "is deprecated, import `SchemaExtension` instead."
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            _warned_extension = True
        return SchemaExtension

    raise AttributeError(f"module {_MODULE_NAME} has no attribute {name}")


__all__ = [
    "AddValidationRules",
    "DisableIntrospection",
    "DisableValidation",
    "FieldExtension",
    "IgnoreContext",
    "LifecycleStep",
    "MaskErrors",
    "MaxAliasesLimiter",
    "MaxTokensLimiter",
    "ParserCache",
    "QueryDepthLimiter",
    "SchemaExtension",
    "ValidationCache",
]

_MODULE_NAME = __name__

_warned_extension = False
