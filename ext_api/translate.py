from typing import TypeVar, Self
from collections.abc import Generator
from random import choice

from argostranslate.translate import Language, ITranslation

Translation = TypeVar("Translation", bound=ITranslation)

class TranslationFailedError(RuntimeError):
    """
    An error occured while attempting to translate.

    Attributes
    ----------
    In a sequenced translation all attributes are taken from the 
    iteration where the error occured.
    + from_lang: `Language`
        The language from which a translation was attempted.
    + to_lang: `Language`
        The language a translation was attempted to.
    + query: `str`
        The translation query.
    """
    def __init__(
            self, 
            from_lang: Language,
            to_lang: Language, 
            query: str,
            *args
        ):
            super().__init__(*args)
            self.from_lang = from_lang
            self.to_lang = to_lang
            self.query = query
    
    @classmethod
    def from_tuple(cls, langs: tuple[Language, Language], query: str) -> Self:
        return cls(langs[0], langs[1], query)

class InvalidTranslationError(TranslationFailedError): 
    """
    A translation was attempted that is not provided by the current
    packages.

    Attributes
    ----------
    In a sequenced translation all attributes are taken from the 
    iteration where the error occured.
    + from_lang: `Language`
        The language from which a translation was attempted.
    + to_lang: `Language`
        The language a translation was attempted to.
    + query: `str`
        The translation query.
    """

def get_random_sequence(
        start: Language, 
        end: Language, 
        steps: int
    ) -> list[Language]:
    """
    Generates a random sequence starting at <start> going over 
    <steps-1> languages before returning to <end>.

    Parameters
    ----------
    + start: `Language`
        The starting language of the sequence. In a translation this
        will be the first from-language.
    + end: `Language`
        The final language for the sequence. In a translation this will
        be the last to-language.
    + steps: `int`
        The number of steps in the sequence. The starting language is
        not counted as one of these, however the ending is.
        In a translation this would be the number of translations.
    """
    raise NotImplementedError

def iterate_translate_sequence(
        sequence: list[Language]
    ) -> Generator[
        tuple[Translation|None, tuple[Language, Language]], 
        None, 
        None
    ]:
    """
    Returns an iterator going through a translation sequence.

    Yields
    ------
    `tuple[Translation|None, tuple[Language, Language]]`

    1. `Translation|None`
        A translation that is part of the sequence.
        `None` if the translation is not provided by the installed
        packages.

    2. `tuple[Language, Language]`
        The (from, to) pair of the translation. This exists even if
        the translation is `None`.
    """
    return (
        (from_lang.get_translation(to_lang), (from_lang, to_lang))
        for from_lang, to_lang in zip(sequence[:-1],sequence[1:])
    )

def identify_invalid_sequence(
        sequence: list[Language]
    ) -> tuple[int, tuple[Language, Language]]|None:
    """
    Checks if a sequence contains an invalid translation and returns
    the first invalid translation and its position.

    This is not guaranteed to find every error, but instead only the 
    first in the sequence.

    Returns
    -------
    `tuple[int, tuple[Language, Language]]|None`
    + The index of the invalid language pair starting with from.
    + The language pair yielding the invalid translation.

    `None` if no invalid translation was found.
    """
    for i, (translation, langs) \
        in enumerate(iterate_translate_sequence(sequence)):
        if translation is None:
            return i, langs

def translate_sequenced(
        query: str,
        sequence: list[Language]
    ) -> str:
    """
    Translates a query through a sequence of languages.
    The first language of the sequence should be the language of origin,
    not the translation target.

    Parameters
    ----------
    + query: `str`
        The query (i.e. text) to be translated
    + sequence: `list[Language]`
        The language sequence for the translation. Every item after the
        first is a translation target, the first element must be the
        language of the query. 

    Returns
    -------
    `str`

    The translation result.
    
    Raises
    ------
    + `InvalidTranslationError`
        The provided sequence is invalid (one of the translations is
        unavailable)
    + `TranslationFailedError`
        A translation attempt failed due to a non-specific reason.
    """
    for translation, langs in iterate_translate_sequence(sequence):
        if translation is None:
            raise InvalidTranslationError.from_tuple(langs, query) 
        try:
            query = translation.translate(query)
        except Exception as e:
            raise TranslationFailedError.from_tuple(langs, query) from e
    return query

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