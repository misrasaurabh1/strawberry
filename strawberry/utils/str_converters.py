import re


# Adapted from this response in Stackoverflow
# http://stackoverflow.com/a/19053800/1072990
def to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    # We capitalize the first letter of each component except the first one
    # with the 'capitalize' method and join them together.
    return components[0] + "".join(x.capitalize() if x else "_" for x in components[1:])


TO_KEBAB_CASE_RE = re.compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")


def to_kebab_case(name: str) -> str:
    return TO_KEBAB_CASE_RE.sub(r"-\1", name).lower()


def capitalize_first(name: str) -> str:
    return name[0].upper() + name[1:]


def to_snake_case(name: str) -> str:
    # Use precompiled regex patterns for improved performance
    name = _pattern1.sub(r"\1_\2", name)
    return _pattern2.sub(r"\1_\2", name).lower()


__all__ = ["capitalize_first", "to_camel_case", "to_kebab_case", "to_snake_case"]

_pattern1 = re.compile(r"(.)([A-Z][a-z]+)")

_pattern2 = re.compile(r"([a-z0-9])([A-Z])")
