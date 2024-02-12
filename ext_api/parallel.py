from collections.abc import Collection
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from argostranslate.translate import Language

from ext_api.translate import (
    translate_sequenced,
    iterate_translate_sequence,
    _translate_sequence_part
)
from ext_api.helpers import split_into_parts, ProgressCounter


class PartiallyFailedTranslation(ExceptionGroup):
    """
    Raised when a parallelised translation has failed tasks.
    Contains an extra `results` attribute with the valid parts of the translation.
    """
    results: list[str|None]
    """
    The result of the translation split up.
    Values may be None in which case that part of the translation failed.
    """
    
    def __new__(cls, message: str, excs: list[Exception], results: list[str|None]):
        obj = super().__new__(cls, message, excs)
        obj.results = results
        return obj


ProgressCallback = Callable[[ProgressCounter], None]

def _parallel_translate_task(
    query: str,
    sequence: list[Language],
    progress: ProgressCounter,
    /
) -> str:
    for translation, langs in iterate_translate_sequence(sequence):
        query = _translate_sequence_part(query, translation, langs)
        progress.increment()
    return query

def parallel_sequenced_translate(
    queries: Collection[str],
    sequence: list[Language],
    /, *,
    pool_size: int|None=None,
    callback: ProgressCallback|None=None
) -> list[str]:
    """
    Translates multiple queries in parallel through a sequence and returns the results in-order.
    
    Parameters
    ----------
    + `queries`
        The queries to be translated.
    + `sequence`
        The translation sequence to execute through
    + `pool_size`
        The maximum amount of parallel translations.
        If set lower then the length of `queries`,
        some queries will be translated in sequence instead.
        Note that this might still occur when the query size is large enough.
    
    Raises
    ------
    + `PartiallyFailedTranslation`
        Raised when one or more translations raised an exception themselves.
        This is an `ExceptionGroup` subclass.
    """
    progress = ProgressCounter(
        end=len(queries)*(len(sequence)-1),
        callback=callback
    )
    if callback is not None:
        callback(progress)
    
    with ThreadPoolExecutor(pool_size, "TranslationThread-") as pool:
        futures = [
            pool.submit(_parallel_translate_task, q, sequence, progress)
            for q in queries
        ]
        results = []
        exceptions = []
        for f in futures:
            try:
                results.append(f.result())
            except Exception as e:
                results.append(None)
                exceptions.append(e)
        if len(exceptions) > 0:
            # Passing more than two arguments is apparently illegal for exception groups >:(
            eg = PartiallyFailedTranslation(
                "Some or all attempts at translation failed",
                exceptions,
                results  # type: ignore
            )
            eg.results = results
            raise eg
        return [
            f.result()
            for f in futures
        ]


def translate_sequence_segmented(
    query: str,
    sequence: list[Language],
    /,
    max_segment_size: int,
    *,
    pool_size: int|None=None,
    callback: ProgressCallback|None=None
) -> str:
    queries = split_into_parts(query, max_segment_size)
    results = parallel_sequenced_translate(
        queries,
        sequence,
        pool_size=pool_size,
        callback=callback
    )
    return "".join(results)