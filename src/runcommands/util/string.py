import re


def camel_to_underscore(name):
    """Convert camel case name to underscore name.

    Examples::

        >>> camel_to_underscore('HttpRequest')
        'http_request'
        >>> camel_to_underscore('httpRequest')
        'http_request'
        >>> camel_to_underscore('HTTPRequest')
        'http_request'
        >>> camel_to_underscore('myHTTPRequest')
        'my_http_request'
        >>> camel_to_underscore('MyHTTPRequest')
        'my_http_request'
        >>> camel_to_underscore('my_http_request')
        'my_http_request'
        >>> camel_to_underscore('MyHTTPRequestXYZ')
        'my_http_request_xyz'
        >>> camel_to_underscore('_HTTPRequest')
        '_http_request'
        >>> camel_to_underscore('Request')
        'request'
        >>> camel_to_underscore('REQUEST')
        'request'
        >>> camel_to_underscore('_Request')
        '_request'
        >>> camel_to_underscore('__Request')
        '__request'
        >>> camel_to_underscore('_request')
        '_request'
        >>> camel_to_underscore('Request_')
        'request_'

    """
    name = re.sub(r"(?<!\b)(?<!_)([A-Z][a-z])", r"_\1", name)
    name = re.sub(r"(?<!\b)(?<!_)([a-z])([A-Z])", r"\1_\2", name)
    name = name.lower()
    return name


def invert_string(string):
    """Invert the logical meaning of a string.

    Examples::

        >>> invert_string('Yes')
        'No'
        >>> invert_string('No')
        'Yes'
        >>> invert_string("don't")
        'do'
        >>> invert_string("don't do thing")
        'do thing'

    """
    first_letter = string[0]
    is_capitalized = first_letter.isupper()
    words = string.split(None, 1)
    first_word = words[0]

    one_word_inversions = {
        "Do": "Don't",
        "Don't": "Do",
        "Do not": "Do",
        "With": "Without",
        "Without": "With",
        "Yes": "No",
        "No": "Yes",
    }
    for k in tuple(one_word_inversions):
        one_word_inversions[k.lower()] = one_word_inversions[k].lower()

    inversions = {
        "Do": "No",
        "Don't": "",
        "Do not": "",
        "With": "Without",
        "Without": "With",
        "No": "With",
    }
    for k in tuple(inversions):
        inversions[k.lower()] = inversions[k].lower()

    if string in one_word_inversions:
        inverted = one_word_inversions[string]
    elif first_word in inversions:
        inverted_first_word = inversions[first_word]
        if inverted_first_word:
            words[0] = inverted_first_word
            i = len(first_word) - len(string)
            inverted = f"{inverted_first_word}{string[i:]}"
        else:
            inverse_help = words[1]
            inverted = inverse_help.capitalize() if is_capitalized else inverse_help
    else:
        inverted_first_word = "Don't" if is_capitalized else "don't"
        inverted = f"{inverted_first_word} {first_letter.lower()}{string[1:]}"

    suffixes = {
        "[y]": "[n]",
        "(y)": "(n)",
        "[yes]": "[no]",
        "(yes)": "(no)",
        "[true]": "[false]",
        "(true)": "(false)",
    }
    for suffix, inverse_suffix in suffixes.items():
        if inverted.endswith(suffix):
            inverted = f"{inverted[: -len(suffix)]}{inverse_suffix}"
        elif inverted.endswith(inverse_suffix):
            inverted = f"{inverted[: -len(inverse_suffix)]}{suffix}"

    return inverted
