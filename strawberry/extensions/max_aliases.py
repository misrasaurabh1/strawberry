from typing import Union

from graphql import (
    ExecutableDefinitionNode,
    FieldNode,
    GraphQLError,
    InlineFragmentNode,
    ValidationContext,
    ValidationRule,
)

from strawberry.extensions.add_validation_rules import AddValidationRules


class MaxAliasesLimiter(AddValidationRules):
    """Add a validator to limit the number of aliases used.

    Example:

    ```python
    import strawberry
    from strawberry.extensions import MaxAliasesLimiter

    schema = strawberry.Schema(Query, extensions=[MaxAliasesLimiter(max_alias_count=15)])
    ```
    """

    def __init__(self, max_alias_count: int) -> None:
        """Initialize the MaxAliasesLimiter.

        Args:
            max_alias_count: The maximum number of aliases allowed in a GraphQL document.
        """
        validator = create_validator(max_alias_count)
        super().__init__([validator])


def create_validator(max_alias_count: int) -> type[ValidationRule]:
    """Create a validator that checks the number of aliases in a document.

    Args:
        max_alias_count: The maximum number of aliases allowed in a GraphQL document.
    """

    class MaxAliasesValidator(ValidationRule):
        def __init__(self, validation_context: ValidationContext) -> None:
            document = validation_context.document
            def_that_can_contain_alias = (
                def_
                for def_ in document.definitions
                if isinstance(def_, (ExecutableDefinitionNode))
            )
            total_aliases = sum(
                count_fields_with_alias(def_node)
                for def_node in def_that_can_contain_alias
            )
            if total_aliases > max_alias_count:
                msg = f"{total_aliases} aliases found. Allowed: {max_alias_count}"
                validation_context.report_error(GraphQLError(msg))

            super().__init__(validation_context)

    return MaxAliasesValidator


def count_fields_with_alias(
    selection_set_owner: Union[ExecutableDefinitionNode, FieldNode, InlineFragmentNode],
) -> int:
    # Fast exit if no selections
    selection_set = selection_set_owner.selection_set
    if selection_set is None:
        return 0

    # Use local variable lookups for slight speedup
    selections = selection_set.selections
    result = 0
    FieldNodeType = FieldNode
    InlineFragmentNodeType = InlineFragmentNode

    for selection in selections:
        selection_type = type(selection)
        is_field = selection_type is FieldNodeType

        # Only check for alias if type is FieldNode
        if is_field and selection.alias:
            result += 1

        # Only recurse if selection_set exists and type is FieldNode or InlineFragmentNode
        # (using type(...) is ... instead of isinstance(...) is faster with only direct types)
        if (is_field or selection_type is InlineFragmentNodeType) and getattr(
            selection, "selection_set", None
        ):
            result += count_fields_with_alias(selection)

    return result


__all__ = ["MaxAliasesLimiter"]
