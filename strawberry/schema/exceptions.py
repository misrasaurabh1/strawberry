from strawberry.types.graphql import OperationType


class CannotGetOperationTypeError(Exception):
    """Internal error raised when we cannot get the operation type from a GraphQL document."""

    def __init__(self, operation_name):
        self.operation_name = operation_name
        if operation_name is None:
            self._reason = "Can't get GraphQL operation type"
        else:
            self._reason = f'Unknown operation named "{operation_name}".'

    def as_http_error_reason(self) -> str:
        return self._reason


class InvalidOperationTypeError(Exception):
    def __init__(self, operation_type: OperationType) -> None:
        self.operation_type = operation_type

    def as_http_error_reason(self, method: str) -> str:
        operation_type = {
            OperationType.QUERY: "queries",
            OperationType.MUTATION: "mutations",
            OperationType.SUBSCRIPTION: "subscriptions",
        }[self.operation_type]

        return f"{operation_type} are not allowed when using {method}"


__all__ = [
    "CannotGetOperationTypeError",
    "InvalidOperationTypeError",
]
