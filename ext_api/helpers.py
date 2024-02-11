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