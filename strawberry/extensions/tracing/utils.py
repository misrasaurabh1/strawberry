from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from graphql import GraphQLResolveInfo

from strawberry.extensions.utils import is_introspection_field
from strawberry.resolvers import is_default_resolver

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo


def should_skip_tracing(resolver: Callable[..., Any], info: GraphQLResolveInfo) -> bool:
    # Pull locals to avoid repeated attribute lookups
    parent_type_fields = info.parent_type.fields
    field_name = info.field_name

    if field_name not in parent_type_fields:
        return True

    # Only lookup resolver once
    resolve = parent_type_fields[field_name].resolve

    # Short-circuit for most likely branch order:
    # 1. Fast return if field is introspection or resolver is None
    # 2. Default resolver check after, as rare
    return (
        is_introspection_field(info) or resolve is None or is_default_resolver(resolve)
    )


__all__ = ["should_skip_tracing"]
