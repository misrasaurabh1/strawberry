from __future__ import annotations

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo


def is_introspection_key(key: Union[str, int]) -> bool:
    # from: https://spec.graphql.org/June2018/#sec-Schema
    # > All types and directives defined within a schema must not have a name which
    # > begins with "__" (two underscores), as this is used exclusively
    # > by GraphQL`s introspection system.

    return str(key).startswith("__")


def is_introspection_field(info: GraphQLResolveInfo) -> bool:
    path = info.path

    while path:
        if is_introspection_key(path.key):
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


def _determine_depth_selection_set(
    selection_set,
    fragments,
    depth_so_far,
    max_depth,
    context,
    operation_name,
    should_ignore,
):
    # Inlined helper for speed: use local vars, avoid generator overhead for very small lists
    selections = selection_set.selections
    # Since we're calling max on a list, using listcomp directly is as fast as generator for short lists
    return max(
        determine_depth(
            node=selection,
            fragments=fragments,
            depth_so_far=depth_so_far,
            max_depth=max_depth,
            context=context,
            operation_name=operation_name,
            should_ignore=should_ignore,
        )
        for selection in selections
    )


__all__ = ["get_path_from_info", "is_introspection_field", "is_introspection_key"]
