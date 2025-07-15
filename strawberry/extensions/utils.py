from __future__ import annotations

from typing import TYPE_CHECKING, Union

from graphql import GraphQLResolveInfo

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo


def is_introspection_key(key: Union[str, int]) -> bool:
    # from: https://spec.graphql.org/June2018/#sec-Schema
    # > All types and directives defined within a schema must not have a name which
    # > begins with "__" (two underscores), as this is used exclusively
    # > by GraphQL`s introspection system.

    return str(key).startswith("__")


def is_introspection_field(info: GraphQLResolveInfo) -> bool:
    # Faster lookup using local variable and inlining the key check
    path = info.path
    while path is not None:
        key = path.key
        if isinstance(key, str):
            if key[:2] == "__":
                return True
        elif str(key).startswith("__"):
            return True
        path = path.prev
    return False


def get_path_from_info(info: GraphQLResolveInfo) -> list[str]:
    path = info.path
    elements = []

    while path:
        elements.append(path.key)
        path = path.prev

    return elements[::-1]


__all__ = ["get_path_from_info", "is_introspection_field", "is_introspection_key"]
