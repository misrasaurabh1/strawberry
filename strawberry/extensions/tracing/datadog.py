from __future__ import annotations

import hashlib
from functools import cached_property
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Callable, Optional

import ddtrace
from ddtrace import tracer
from graphql import GraphQLResolveInfo
from packaging import version

from strawberry.extensions import LifecycleStep, SchemaExtension
from strawberry.extensions.tracing.utils import should_skip_tracing
from strawberry.extensions.utils import is_introspection_field
from strawberry.resolvers import is_default_resolver
from strawberry.types.execution import ExecutionContext

parsed_ddtrace_version = version.parse(ddtrace.__version__)
if parsed_ddtrace_version >= version.parse("3.0.0"):
    from ddtrace.trace import Span, tracer
else:
    from ddtrace import Span, tracer


if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

    from graphql import GraphQLResolveInfo

    from strawberry.types.execution import ExecutionContext


class DatadogTracingExtension(SchemaExtension):
    def __init__(
        self,
        *,
        execution_context: Optional[ExecutionContext] = None,
    ) -> None:
        # Only set if provided, otherwise don't add attribute
        if execution_context is not None:
            self.execution_context = execution_context

    @cached_property
    def _resource_name(self) -> str:
        if self.execution_context.query is None:
            return "query_missing"

        query_hash = self.hash_query(self.execution_context.query)

        if self.execution_context.operation_name:
            return f"{self.execution_context.operation_name}:{query_hash}"

        return query_hash

    def create_span(
        self,
        lifecycle_step: LifecycleStep,
        name: str,
        **kwargs: Any,
    ) -> Span:
        """Create a span with the given name and kwargs.

        You can  override this if you want to add more tags to the span.

        Example:

        ```python
        class CustomExtension(DatadogTracingExtension):
            def create_span(self, lifecycle_step, name, **kwargs):
                span = super().create_span(lifecycle_step, name, **kwargs)
                if lifecycle_step == LifeCycleStep.OPERATION:
                    span.set_tag("graphql.query", self.execution_context.query)
                return span
        ```
        """
        # Tracer always returns a Span, span_type overridable via kwargs
        return tracer.trace(
            name,
            span_type="graphql",
            **kwargs,
        )

    def hash_query(self, query: str) -> str:
        return hashlib.md5(query.encode("utf-8")).hexdigest()  # noqa: S324

    def on_operation(self) -> Iterator[None]:
        self._operation_name = self.execution_context.operation_name
        span_name = (
            f"{self._operation_name}" if self._operation_name else "Anonymous Query"
        )

        self.request_span = self.create_span(
            LifecycleStep.OPERATION,
            span_name,
            resource=self._resource_name,
            service="strawberry",
        )
        self.request_span.set_tag("graphql.operation_name", self._operation_name)

        query = self.execution_context.query

        if query is not None:
            query = query.strip()
            operation_type = "query"

            if query.startswith("mutation"):
                operation_type = "mutation"
            elif query.startswith("subscription"):  # pragma: no cover
                operation_type = "subscription"
        else:
            operation_type = "query_missing"

        self.request_span.set_tag("graphql.operation_type", operation_type)

        yield

        self.request_span.finish()

    def on_validate(self) -> Generator[None, None, None]:
        self.validation_span = self.create_span(
            lifecycle_step=LifecycleStep.VALIDATION,
            name="Validation",
        )
        yield
        self.validation_span.finish()

    def on_parse(self) -> Generator[None, None, None]:
        self.parsing_span = self.create_span(
            lifecycle_step=LifecycleStep.PARSE,
            name="Parsing",
        )
        yield
        self.parsing_span.finish()

    async def resolve(
        self,
        _next: Callable,
        root: Any,
        info: GraphQLResolveInfo,
        *args: str,
        **kwargs: Any,
    ) -> Any:
        if should_skip_tracing(_next, info):
            result = _next(root, info, *args, **kwargs)

            if isawaitable(result):  # pragma: no cover
                result = await result

            return result

        field_path = f"{info.parent_type}.{info.field_name}"

        with self.create_span(
            lifecycle_step=LifecycleStep.RESOLVE,
            name=f"Resolving: {field_path}",
        ) as span:
            span.set_tag("graphql.field_name", info.field_name)
            span.set_tag("graphql.parent_type", info.parent_type.name)
            span.set_tag("graphql.field_path", field_path)
            span.set_tag("graphql.path", ".".join(map(str, info.path.as_list())))

            result = _next(root, info, *args, **kwargs)

            if isawaitable(result):
                result = await result

            return result


class DatadogTracingExtensionSync(DatadogTracingExtension):
    def resolve(
        self,
        _next: Callable,
        root: Any,
        info: GraphQLResolveInfo,
        *args: str,
        **kwargs: Any,
    ) -> Any:
        # Inline should_skip_tracing for minimal attribute lookups and branching
        parent_type = info.parent_type
        fields = parent_type.fields
        field_name = info.field_name

        resolver = None
        if field_name in fields:
            resolver = fields[field_name].resolve

        # Short-circuit for fast skip tracing detection
        # Note: The original called is_introspection_field and is_default_resolver ONLY if the resolver exists.
        skip = (
            field_name not in fields
            or is_introspection_field(info)
            or resolver is None
            or is_default_resolver(resolver)
        )
        if skip:
            return _next(root, info, *args, **kwargs)

        # Preparing data for tag efficiently up front
        parent_type_name = parent_type.name
        # f"{info.parent_type}.{info.field_name}" is pythonic, but .__repr__ might be costly: get name directly.
        field_path = f"{parent_type_name}.{field_name}"
        path_list = info.path.as_list()  # Only call as_list once
        graphql_path = ".".join(map(str, path_list))

        # Create and mark span, set relevant tags in minimal dictionary/setter calls
        with self.create_span(
            lifecycle_step=LifecycleStep.RESOLVE,
            name=f"Resolving: {field_path}",
        ) as span:
            # Set all tags immediately; string formatting is done above
            span.set_tag("graphql.field_name", field_name)
            span.set_tag("graphql.parent_type", parent_type_name)
            span.set_tag("graphql.field_path", field_path)
            span.set_tag("graphql.path", graphql_path)

            return _next(root, info, *args, **kwargs)


__all__ = ["DatadogTracingExtension", "DatadogTracingExtensionSync"]
