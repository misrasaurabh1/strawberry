# This is a Python port of https://github.com/stems/graphql-depth-limit
# which is licensed under the terms of the MIT license, reproduced below.
#
# -----------
#
# MIT License
#
# Copyright (c) 2017 Stem
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Callable,
    Optional,
    Union,
)

from graphql import GraphQLError
from graphql.language import (
    BooleanValueNode,
    DefinitionNode,
    FieldNode,
    FloatValueNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    InlineFragmentNode,
    IntValueNode,
    ListValueNode,
    Node,
    ObjectValueNode,
    OperationDefinitionNode,
    StringValueNode,
    ValueNode,
)
from graphql.validation import ValidationContext, ValidationRule

from strawberry.extensions import AddValidationRules
from strawberry.extensions.utils import is_introspection_key

if TYPE_CHECKING:
    from collections.abc import Iterable

IgnoreType = Union[Callable[[str], bool], re.Pattern, str]

FieldArgumentType = Union[
    bool, int, float, str, list["FieldArgumentType"], dict[str, "FieldArgumentType"]
]
FieldArgumentsType = dict[str, FieldArgumentType]


@dataclass
class IgnoreContext:
    field_name: str
    field_args: FieldArgumentsType
    node: Node
    context: ValidationContext


ShouldIgnoreType = Callable[[IgnoreContext], bool]


class QueryDepthLimiter(AddValidationRules):
    """Add a validator to limit the query depth of GraphQL operations.

    Example:

    ```python
    import strawberry
    from strawberry.extensions import QueryDepthLimiter

    schema = strawberry.Schema(
        Query,
        extensions=[QueryDepthLimiter(max_depth=4)],
    )
    ```
    """

    def __init__(
        self,
        max_depth: int,
        callback: Optional[Callable[[dict[str, int]], None]] = None,
        should_ignore: Optional[ShouldIgnoreType] = None,
    ) -> None:
        """Initialize the QueryDepthLimiter.

        Args:
            max_depth: The maximum allowed depth for any operation in a GraphQL document.
            callback: Called each time validation runs.
                Receives an Object which is a map of the depths for each operation.
            should_ignore: Stops recursive depth checking based on a field name and arguments.
                A function that returns a boolean and conforms to the ShouldIgnoreType function signature.
        """
        if should_ignore is not None and not callable(should_ignore):
            raise TypeError(
                "The `should_ignore` argument to "
                "`QueryDepthLimiter` must be a callable."
            )
        validator = create_validator(max_depth, should_ignore, callback)
        super().__init__([validator])


def create_validator(
    max_depth: int,
    should_ignore: Optional[ShouldIgnoreType],
    callback: Optional[Callable[[dict[str, int]], None]] = None,
) -> type[ValidationRule]:
    class DepthLimitValidator(ValidationRule):
        def __init__(self, validation_context: ValidationContext) -> None:
            document = validation_context.document
            definitions = document.definitions

            fragments = get_fragments(definitions)
            queries = get_queries_and_mutations(definitions)
            query_depths = {}

            for query in queries:
                query_depths[query] = determine_depth(
                    node=queries[query],
                    fragments=fragments,
                    depth_so_far=0,
                    max_depth=max_depth,
                    context=validation_context,
                    operation_name=query,
                    should_ignore=should_ignore,
                )

            if callable(callback):
                callback(query_depths)
            super().__init__(validation_context)

    return DepthLimitValidator


def get_fragments(
    definitions: Iterable[DefinitionNode],
) -> dict[str, FragmentDefinitionNode]:
    fragments = {}
    for definition in definitions:
        if isinstance(definition, FragmentDefinitionNode):
            fragments[definition.name.value] = definition

    return fragments


# This will actually get both queries and mutations.
# We can basically treat those the same
def get_queries_and_mutations(
    definitions: Iterable[DefinitionNode],
) -> dict[str, OperationDefinitionNode]:
    operations = {}

    for definition in definitions:
        if isinstance(definition, OperationDefinitionNode):
            operation = definition.name.value if definition.name else "anonymous"
            operations[operation] = definition

    return operations


def get_field_name(
    node: FieldNode,
) -> str:
    # Micro-optimized: direct attribute reference, avoid ternary
    alias = node.alias
    if alias:
        return alias.value
    return node.name.value


def resolve_field_value(
    value: ValueNode,
) -> FieldArgumentType:
    if isinstance(value, StringValueNode):
        return value.value
    if isinstance(value, IntValueNode):
        return int(value.value)
    if isinstance(value, FloatValueNode):
        return float(value.value)
    if isinstance(value, BooleanValueNode):
        return value.value
    if isinstance(value, ListValueNode):
        return [resolve_field_value(v) for v in value.values]
    if isinstance(value, ObjectValueNode):
        return {v.name.value: resolve_field_value(v.value) for v in value.fields}
    return {}


def get_field_arguments(
    node: FieldNode,
) -> FieldArgumentsType:
    # Optimized: avoid local dict type annotation, listcomp to dict
    if not node.arguments:
        return {}
    return {arg.name.value: resolve_field_value(arg.value) for arg in node.arguments}


def determine_depth(
    node: Node,
    fragments: dict[str, FragmentDefinitionNode],
    depth_so_far: int,
    max_depth: int,
    context: ValidationContext,
    operation_name: str,
    should_ignore: Optional[ShouldIgnoreType],
) -> int:
    # Reorder fast path first to allow early bail
    if depth_so_far > max_depth:
        context.report_error(
            GraphQLError(
                f"'{operation_name}' exceeds maximum operation depth of {max_depth}",
                [node],
            )
        )
        return depth_so_far

    # Using type() instead of isinstance() can be a micro-optimization, but not reliable with subclassing
    if isinstance(node, FieldNode):
        # Fast path: check is_introspection_key before anything else
        node_name = node.name.value
        if is_introspection_key(node_name):
            should_ignore_field = True
        elif should_ignore is not None:
            # Only get arguments/names if needed
            should_ignore_field = should_ignore(
                IgnoreContext(
                    get_field_name(node),
                    get_field_arguments(node),
                    node,
                    context,
                )
            )
        else:
            should_ignore_field = False

        selection_set = node.selection_set
        # Early exit if introspection or ignore or no selection_set
        if should_ignore_field or not selection_set:
            return 0

        # Use optimized helper to avoid repeatedly accessing attributes
        return 1 + _determine_depth_selection_set(
            selection_set=selection_set,
            fragments=fragments,
            depth_so_far=depth_so_far + 1,
            max_depth=max_depth,
            context=context,
            operation_name=operation_name,
            should_ignore=should_ignore,
        )

    # FragmentSpreadNode
    if isinstance(node, FragmentSpreadNode):
        # Avoid unnecessary dict lookups by storing in local
        frag = fragments[node.name.value]
        return determine_depth(
            node=frag,
            fragments=fragments,
            depth_so_far=depth_so_far,
            max_depth=max_depth,
            context=context,
            operation_name=operation_name,
            should_ignore=should_ignore,
        )

    # InlineFragmentNode, FragmentDefinitionNode, OperationDefinitionNode
    if isinstance(
        node, (InlineFragmentNode, FragmentDefinitionNode, OperationDefinitionNode)
    ):
        # Use optimized helper
        return _determine_depth_selection_set(
            selection_set=node.selection_set,
            fragments=fragments,
            depth_so_far=depth_so_far,
            max_depth=max_depth,
            context=context,
            operation_name=operation_name,
            should_ignore=should_ignore,
        )

    # Error case
    raise TypeError(f"Depth crawler cannot handle: {node.kind}")  # pragma: no cover


def is_ignored(node: FieldNode, ignore: Optional[list[IgnoreType]] = None) -> bool:
    if ignore is None:
        return False

    for rule in ignore:
        field_name = node.name.value
        if isinstance(rule, str):
            if field_name == rule:
                return True
        elif isinstance(rule, re.Pattern):
            if rule.match(field_name):
                return True
        elif callable(rule):
            if rule(field_name):
                return True
        else:
            raise TypeError(f"Invalid ignore option: {rule}")

    return False


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


__all__ = ["QueryDepthLimiter"]
