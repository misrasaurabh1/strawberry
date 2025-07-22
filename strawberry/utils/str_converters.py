import re


# Adapted from this response in Stackoverflow
# http://stackoverflow.com/a/19053800/1072990
def to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    if len(components) == 1:
        return snake_str
    first = components[0]
    rest = components[1:]
    # Pre-allocate list for fast concatenation and avoid generator expression
    result = [first]
    capitalize = str.capitalize
    for x in rest:
        if x:
            result.append(capitalize(x))
        else:
            result.append("_")
    return "".join(result)


TO_KEBAB_CASE_RE = re.compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")


def to_kebab_case(name: str) -> str:
    return TO_KEBAB_CASE_RE.sub(r"-\1", name).lower()


def capitalize_first(name: str) -> str:
    return name[0].upper() + name[1:]


def to_snake_case(name: str) -> str:
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


__all__ = ["capitalize_first", "to_camel_case", "to_kebab_case", "to_snake_case"]
