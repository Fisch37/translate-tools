from argparse import ArgumentParser, FileType
from os import environ
from sys import exit, stderr

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
    type=FileType("r", encoding="utf-8"),
    required=False,
    default="-",
)
parser.add_argument(
    "--output", "-o",
    help="The file to output the translation into. If left unset, outputs to stdout instead",
    type=FileType("w", encoding="utf-8"),
    required=False,
    default="-"
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
    print(f"\r{progress.state}/{progress.end}", end="", flush=True)

def main() -> int:
    namespace = parser.parse_args()
    if namespace.gpu:
        environ["ARGOS_DEVICE_TYPE"] = "cuda"
    segment_length: int = namespace.segment_size
    pool_size: int|None = namespace.pool_size
    with namespace.input as file:
        query: str = file.read()
    output = namespace.output
    silent: int = namespace.silent
    
    
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