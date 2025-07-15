from __future__ import annotations

import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from strawberry.codegen import CodegenFile, QueryCodegenPlugin
from strawberry.codegen.types import (
    GraphQLEnum,
    GraphQLField,
    GraphQLList,
    GraphQLObjectType,
    GraphQLOptional,
    GraphQLScalar,
    GraphQLType,
    GraphQLUnion,
)

if TYPE_CHECKING:
    from pathlib import Path

    from strawberry.codegen.types import GraphQLField, GraphQLOperation, GraphQLType


class TypeScriptPlugin(QueryCodegenPlugin):
    SCALARS_TO_TS_TYPE: ClassVar[dict[str | type, str]] = {
        "ID": "string",
        "Int": "number",
        "String": "string",
        "Float": "number",
        "Boolean": "boolean",
        "UUID": "string",
        "Date": "string",
        "DateTime": "string",
        "Time": "string",
        "Decimal": "string",
        str: "string",
        float: "number",
    }

    def __init__(self, query: Path) -> None:
        self.outfile_name: str = query.with_suffix(".ts").name
        self.query = query

        # Memoization cache for type name conversions
        self._type_name_cache = {}

    def generate_code(
        self, types: list[GraphQLType], operation: GraphQLOperation
    ) -> list[CodegenFile]:
        printed_types = list(filter(None, (self._print_type(type) for type in types)))

        return [CodegenFile(self.outfile_name, "\n\n".join(printed_types))]

    def _get_type_name(self, type_: GraphQLType) -> str:
        # Use id(type_) as key since instances are not hashable and
        # because GraphQLType objects are reused for identical schema types
        cache = self._type_name_cache
        type_id = id(type_)
        if type_id in cache:
            return cache[type_id]

        # Restructure checks so the fastest most common types are checked first
        # GraphQLScalar and GraphQLObjectType are far more likely than unions/lists

        # Fast path: scalar types with known mapping
        if isinstance(type_, GraphQLScalar):
            scalar_type = self.SCALARS_TO_TS_TYPE.get(type_.name)
            if scalar_type is not None:
                cache[type_id] = scalar_type
                return scalar_type

        # Fast path: object or enum
        if isinstance(type_, (GraphQLObjectType, GraphQLEnum)):
            cache[type_id] = type_.name
            return type_.name

        # Union type
        if isinstance(type_, GraphQLUnion):
            cache[type_id] = type_.name
            return type_.name

        # Optional: memoize recursive result
        if isinstance(type_, GraphQLOptional):
            val = self._get_type_name(type_.of_type) + " | undefined"
            cache[type_id] = val
            return val

        # List type: avoid unnecessary formatting
        if isinstance(type_, GraphQLList):
            child_type = self._get_type_name(type_.of_type)
            if "|" in child_type:
                child_type = f"({child_type})"
            val = f"{child_type}[]"
            cache[type_id] = val
            return val

        # Fallback: unrecognized type, just return its name
        cache[type_id] = type_.name
        return type_.name

    def _print_field(self, field: GraphQLField) -> str:
        name = field.name
        if field.alias:
            # Optimization: avoid redundant formatting when alias is empty/None
            name = f"// alias for {field.name}\n{field.alias}"
        # Elide local variable, keep tight loop
        return f"{name}: {self._get_type_name(field.type)}"

    def _print_enum_value(self, value: str) -> str:
        return f'{value} = "{value}",'

    def _print_object_type(self, type_: GraphQLObjectType) -> str:
        fields = "\n".join(self._print_field(field) for field in type_.fields)

        return "\n".join(
            [f"type {type_.name} = {{", textwrap.indent(fields, " " * 4), "}"],
        )

    def _print_enum_type(self, type_: GraphQLEnum) -> str:
        values = "\n".join(self._print_enum_value(value) for value in type_.values)

        return "\n".join(
            [
                f"enum {type_.name} {{",
                textwrap.indent(values, " " * 4),
                "}",
            ]
        )

    def _print_scalar_type(self, type_: GraphQLScalar) -> str:
        if type_.name in self.SCALARS_TO_TS_TYPE:
            return ""

        assert type_.python_type is not None
        return f"type {type_.name} = {self.SCALARS_TO_TS_TYPE[type_.python_type]}"

    def _print_union_type(self, type_: GraphQLUnion) -> str:
        return f"type {type_.name} = {' | '.join([t.name for t in type_.types])}"

    def _print_type(self, type_: GraphQLType) -> str:
        if isinstance(type_, GraphQLUnion):
            return self._print_union_type(type_)

        if isinstance(type_, GraphQLObjectType):
            return self._print_object_type(type_)

        if isinstance(type_, GraphQLEnum):
            return self._print_enum_type(type_)

        if isinstance(type_, GraphQLScalar):
            return self._print_scalar_type(type_)

        raise ValueError(f"Unknown type: {type}")  # pragma: no cover
