from argostranslate.translate import get_installed_languages, Language

LanguageOrStr = Language|str


def get_lang_from_code(code: str) -> Language:
    """
    Returns a Language object matching the passed code.
    
    Raises
    ------
    + `ValueError`
        The code does not match any installed languages.
    """
    langs = get_installed_languages()
    try:
        return next(filter(lambda l: l.code == code,langs))
    except StopIteration as e:
        raise ValueError(f"Invalid language code {code}") from e

def ensure_language(lang_or_code: LanguageOrStr) -> Language:
    """
    Returns a Language object if a code was passed
    or the input otherwise.
    
    Raises
    ------
    + `ValueError`
        A code was passed that doesn't match any installed languages.
    """
    if isinstance(lang_or_code, str):
        return get_lang_from_code(lang_or_code)
    else: 
        return lang_or_code

def ensure_code(lang_or_code: LanguageOrStr) -> str:
    """
    Returns the code of the language that was passed in.
    Language codes are passed through as-is.
    
    This function is the inverse of `ensure_language`.
    """
    if isinstance(lang_or_code, Language):
        return lang_or_code.code
    else:
        return lang_or_code


def split_into_parts(text: str, target_length: int) -> list[str]:
    """
    Splits a given string into segments that are each shorter or exactly
    <target_length>. 
    Splitting will attempt to seperate on linebreaks or whitespaces 
    if possible, but will split on arbitrary characters when required.
    """
    paragraphs = [""]
    parsable_lines = text.splitlines(keepends=True)
    while len(parsable_lines) > 0:
        current_line = parsable_lines.pop(0)
        if len(current_line) + len(paragraphs[-1]) <= target_length:
            paragraphs[-1] += current_line
        elif len(current_line) <= target_length:
            paragraphs.append(current_line)
        else:
            new_paragraph, remaining_segments = _join_up_to_length(
                current_line.split(" "),
                " ",
                target_length
            )
            if len(new_paragraph) == 0:
                paragraphs.append(current_line[:target_length])
                parsable_lines.insert(0,current_line[target_length:])
            else:
                paragraphs.append(new_paragraph)
                parsable_lines.insert(0," ".join(remaining_segments))
    return paragraphs

def _join_up_to_length(
        segments: list[str], 
        join_char: str,
        length: int,
        /
    ) -> tuple[str, list[str]]:
    """"""
    result = ""
    used_join_char = ""
    while len(segments) > 0 \
        and len(result) + len(used_join_char) + len(segments[0]) <= length:
        result += used_join_char + segments.pop(0)
        used_join_char = join_char
    return result, segments