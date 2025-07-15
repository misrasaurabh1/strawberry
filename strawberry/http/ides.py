import pathlib
from typing import Optional
from typing_extensions import Literal

GraphQL_IDE = Literal["graphiql", "apollo-sandbox", "pathfinder"]


def get_graphql_ide_html(
    graphql_ide: Optional[GraphQL_IDE] = "graphiql",
) -> str:
    # Use local variable for lookup minimization
    cache = _html_cache

    if graphql_ide not in cache:
        # Precompute the static paths for each IDE type as a tuple, indexing by string
        base_path = pathlib.Path(__file__).parents[1]
        if graphql_ide == "apollo-sandbox":
            path = base_path / "static/apollo-sandbox.html"
        elif graphql_ide == "pathfinder":
            path = base_path / "static/pathfinder.html"
        else:
            path = base_path / "static/graphiql.html"
        cache[graphql_ide] = path.read_text(encoding="utf-8")
    return cache[graphql_ide]


__all__ = ["GraphQL_IDE", "get_graphql_ide_html"]

_html_cache = {}
