from typing import TypeVar, Self
from collections.abc import Generator, Sequence
from random import choice

from argostranslate.translate import Language, ITranslation

from ext_api.helpers import ensure_language, LanguageOrStr

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
        steps: int,
        *,
        disabled_languages: Sequence[LanguageOrStr] = (),
        allow_self_translation: bool=True
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
    disabled_languages_set = set(ensure_language(l) for l in disabled_languages)
    next_nodes = [
        t.to_lang
        for t in start.translations_from
        if t.to_lang not in disabled_languages_set
    ]
    if steps == 0:
        if end in next_nodes:
            return [end]
        else:
            raise KeyError(f"Cannot reach end {end} from {start}")
    
    if not allow_self_translation:
        try:
            next_nodes.remove(start)
        except ValueError: ...
    while True:
        try:
            chosen_node = choice(next_nodes)
        except IndexError as e:
            raise KeyError(f"Encountered dead branch whilst generating random sequence")
        try:
            return [start] + get_random_sequence(
                chosen_node,
                end,
                steps - 1,
                disabled_languages=disabled_languages,
                allow_self_translation=allow_self_translation
            )
        except KeyError:
            next_nodes.remove(chosen_node)
            continue

def iterate_translate_sequence(
        sequence: list[Language]
    ) -> Generator[
        tuple[ITranslation|None, tuple[Language, Language]], 
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
