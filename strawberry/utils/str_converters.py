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
    # Fast path for already lowercase or empty
    if not name or name.islower():
        return name

    chars = []
    prev = ""
    for i, c in enumerate(name):
        if c.isupper():
            if i > 0 and (prev.islower() or prev.isdigit()):
                chars.append("-")
            elif i > 0 and (i + 1 < len(name)) and name[i + 1].islower():
                chars.append("-")
            chars.append(c.lower())
        else:
            chars.append(c)
        prev = c
    return "".join(chars)


def capitalize_first(name: str) -> str:
    return name[0].upper() + name[1:]


def to_snake_case(name: str) -> str:
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


__all__ = ["capitalize_first", "to_camel_case", "to_kebab_case", "to_snake_case"]
