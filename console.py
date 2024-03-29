from argparse import ArgumentParser
from io import TextIOWrapper
from itertools import repeat
from os import environ
from pathlib import Path
from sys import exit, stdin, stderr
from typing import Iterable
from shutil import get_terminal_size

from tqdm import tqdm

from ext_api.helpers import ProgressCounter, ensure_language
from ext_api.translate import get_random_sequence
from ext_api.parallel import translate_sequence_segmented

parser = ArgumentParser(
    "Auto Translate Console",
    description="Parallelised translation using ArgosTranslate",
)
parser.add_argument(
    "--pool-size", "-P",
    help="The maximum size of the used thread pool. Optimal value is calculated automatically. \
        Too high or low values may result in significant slowdowns.",
    type=int,
)
parser.add_argument(
    "--segment-size", "-S",
    help="The maximum size of a translation segment. Default value is 2048.\
        Note that segments will be split intelligently on line breaks where possible.\
        This value should be considered an upper bound.",
    type=int,
    default=2048
)
parser.add_argument(
    "--gpu", "-A",
    help="Whether to use hardware-acceleration. Note that this is not supported on all systems.",
    action="store_true"
)
parser.add_argument(
    "--input", "-i",
    help="The source file to read query from. If left unset, data is read from stdin.\
        Note that using this as an interactive application you will have to feed EOF \
        using Ctrl+D (on POSIX) or Ctrl+Z + Enter (on Windows)",
    type=Path,
    required=False,
    default=None,
)
parser.add_argument(
    "--output", "-o",
    help="The file to output the translation into. If left unset, outputs to stdout instead",
    type=Path,
    required=False,
    default=None
)
parser.add_argument(
    "--silent", "-s",
    help="If set, supresses the progress updates for easy command line interpretation.",
    action="count",
    default=0
)
subparsers = parser.add_subparsers(dest="subparser")

simple_translate = subparsers.add_parser(
    "translate",
    help="Simple parallelised translation from one language to another"
)
simple_translate.add_argument(
    "--from", "-f",
    help="The language of the query",
    required=True,
    dest="from_"
)
simple_translate.add_argument(
    "--to", "-t",
    help="The language to translate to",
    required=True
)

jamble_translate = subparsers.add_parser(
    "jamble",
    help="Run a query through a randomised set of languages\
        to get complete nonsense out the other side."
)
jamble_translate.add_argument(
    "--translations", "-n",
    help="The number of translations to pass through",
    type=int,
    required=True,
)
jamble_translate.add_argument(
    "--from", "-f",
    help="The language of the query",
    required=True,
    dest="from_"
)
jamble_translate.add_argument(
    "--except", "-e",
    help="Language code to not use in translations. Consumes any arguments after it \
        and disables Greek and Azerbaijani by default.",
    nargs="*",
    default=["el", "az"],
    dest="except_"
)
jamble_translate.add_argument(
    "--allow-self-translation",
    help="If set, allows random translations from a language to itself.",
    action="store_true"
)


def progress_callback(progress: ProgressCounter):
    tqdm(
        total=progress.end,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}",
    ).update(progress.state)

def iterate_through_files(path: Path):
    for subpath in filter(lambda p: p.is_file(), path.iterdir()):
        with subpath.open("r", encoding="utf-8") as file:
            yield file.read()

def iterate_new_file_objects(destination: Path, pattern: Path):
    for p in pattern.iterdir():
        path = destination / p.name
        file = path.open("w", encoding="utf-8")
        yield file
        file.close()

def repeat_file_object(source: Path):
    while True:
        with source.open("a", encoding="utf-8") as file:
            yield file
            file.write("\n\n")

def main() -> int:
    namespace = parser.parse_args()
    if namespace.gpu:
        environ["ARGOS_DEVICE_TYPE"] = "cuda"
    segment_length: int = namespace.segment_size
    pool_size: int|None = namespace.pool_size
    input_path: Path|None = namespace.input
    output_path: Path|None = namespace.output
    silent: int = namespace.silent
    
    # Generate translation sequence
    if namespace.subparser == "translate":
        try:
            sequence = [
                ensure_language(namespace.from_),
                ensure_language(namespace.to)
            ]
        except ValueError as e:
            print(e, file=stderr)
            return 103
    elif namespace.subparser == "jamble":
        try:
            source_lang = ensure_language(namespace.from_)
            disabled_languages = [
                ensure_language(code)
                for code in namespace.except_
            ]
        except ValueError as e:
            print(e, file=stderr)
            return 103
        sequence = get_random_sequence(
            source_lang,
            source_lang,
            namespace.translations,
            disabled_languages=disabled_languages,
            allow_self_translation=namespace.allow_self_translation
        )
        if silent < 2:
            print(*(str(s) for s in sequence), sep=" -> ")
    else:
        print(NotImplementedError("Unknown action"), file=stderr)
        return 100
    
    # Setup IO
    queries: Iterable[str]
    has_multiple_inputs = False
    if input_path is None:
        queries = (stdin.read(), )
    elif input_path.is_dir():
        queries = iterate_through_files(input_path)
        has_multiple_inputs = True
    else:
        with input_path.open("r", encoding="utf-8") as file:
            queries = (file.read(), )

    outputs: Iterable[TextIOWrapper|None]
    if output_path is None:
        outputs = repeat(None)
    elif output_path.is_dir():
        if not has_multiple_inputs:
            print("Cannot write single-source output to directory", file=stderr)
            return 104
        outputs = iterate_new_file_objects(output_path, input_path)
    else:
        outputs = repeat_file_object(output_path)

    # Translate
    for query, output in zip(queries, outputs):
        result = translate_sequence_segmented(
            query,
            sequence,
            max_segment_size=segment_length,
            pool_size=pool_size,
            callback=progress_callback if silent == 0 else None
        )
        print(result, file=output)
    return 0

if __name__ == "__main__":
    exit(main())