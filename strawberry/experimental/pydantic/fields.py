from __future__ import annotations

import builtins
from types import UnionType as TypingUnionType
from typing import Annotated, Any, Union
from typing import GenericAlias as TypingGenericAlias

from pydantic import BaseModel

from strawberry.experimental.pydantic._compat import (
    PydanticCompat,
    get_args,
    get_origin,
    lenient_issubclass,
)
from strawberry.experimental.pydantic.exceptions import (
    UnregisteredTypeException,
)
from strawberry.types.base import StrawberryObjectDefinition

try:
    from types import UnionType as TypingUnionType
except ImportError:
    import sys

    if sys.version_info < (3, 10):
        TypingUnionType = ()
    else:
        raise


def replace_pydantic_types(type_: Any, is_input: bool) -> Any:
    if lenient_issubclass(type_, BaseModel):
        attr = "_strawberry_input_type" if is_input else "_strawberry_type"
        if hasattr(type_, attr):
            return getattr(type_, attr)
        raise UnregisteredTypeException(type_)
    return type_


def replace_types_recursively(
    type_: Any, is_input: bool, compat: PydanticCompat
) -> Any:
    """Runs the conversions recursively into the arguments of generic types if any."""
    basic_type = compat.get_basic_type(type_)
    replaced_type = replace_pydantic_types(basic_type, is_input)

    origin = get_origin(type_)
    if not origin or not hasattr(type_, "__args__"):
        return replaced_type

    # Cache get_args so it's not called multiple times for replaced_type
    replaced_args = get_args(replaced_type)
    # Fast check: avoid unnecessary tuple(map) allocations
    converted = []
    has_changes = False
    for i, t in enumerate(replaced_args):
        rec = replace_types_recursively(t, is_input=is_input, compat=compat)
        converted.append(rec)
        if rec is not t:
            has_changes = True
    converted = tuple(converted)

    # If no changes, and replaced_type is already built correctly, skip further expensive ops.
    if not has_changes and replaced_type == type_:
        return replaced_type

    if isinstance(replaced_type, TypingGenericAlias):
        return TypingGenericAlias(origin, converted)
    if isinstance(replaced_type, TypingUnionType):
        return Union[converted]

    # TODO: investigate if we could move the check for annotated to the top
    if origin is Annotated and converted:
        converted = (converted[0],)

    # Only call copy_with if necessary (expensive op)
    replaced_type = replaced_type.copy_with(converted)

    if isinstance(replaced_type, StrawberryObjectDefinition):
        # TODO: Not sure if this is necessary. No coverage in tests
        # TODO: Unnecessary with StrawberryObject
        replaced_type = builtins.type(
            replaced_type.name,
            (),
            {"__strawberry_definition__": replaced_type},
        )

    return replaced_type
