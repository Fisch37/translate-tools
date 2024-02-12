from os import environ
environ["ARGOS_DEVICE_TYPE"] = "cuda"

from pathlib import Path

from ext_api.helpers import ensure_language
from ext_api.translate import get_random_sequence
from ext_api.parallel import translate_sequence_segmented

lang = ensure_language("de")


source = Path("files")
output = Path("translated")

skip = False
for target in source.iterdir():
    if skip:
        skip = False
        continue
    
    sequence = get_random_sequence(
        lang,
        lang,
        15,
        disabled_languages=["el"],  # Greek translations are... weird
        allow_self_translation=False
    )
    sequence_str = " -> ".join(
        str(l)
        for l in sequence
    )
    print(sequence_str)
    with target.open(encoding="ansi") as file:
        query = file.read()

    result = translate_sequence_segmented(
        query,
        sequence,
        1024*2,
        callback=lambda progress: print(f"\r{progress.state}/{progress.end}", end="", flush=True)
    )
    
    with output.joinpath(target.name).open("w", encoding="utf-8") as file:
        file.write(sequence_str)
        file.write("\n\n")
        file.write(result)
    print()