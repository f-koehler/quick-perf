import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer()
logger = logging.getLogger(__name__)

default_path = Path("perf_data")


@app.command()
def main(
    target: Annotated[Path, typer.Argument()],
    arguments: Annotated[list[str], typer.Argument()] = [],
    force: Annotated[bool, typer.Option("-f", "--force")] = False,
    frequency: Annotated[int, typer.Option("-F", "--frequency")] = 999,
    output_path: Annotated[Path, typer.Option("-o", "--output")] = default_path,
):
    path_perf = shutil.which("perf")
    if not path_perf:
        logger.error("Failed to find perf")
        raise typer.Exit(code=1)
    path_stackcollapse = shutil.which("stackcollapse-perf.pl")
    if not path_stackcollapse:
        logger.error("Failed to find stackcollapse-perf.pl")
        raise typer.Exit(code=1)
    path_flamegraph = shutil.which("flamegraph.pl")
    if not path_flamegraph:
        logger.error("Failed to find flamegraph.pl")
        raise typer.Exit(code=1)

    target = target.absolute()
    if not target.exists():
        logger.error(f"Profiling target not found: {target}")
        raise typer.Exit(code=1)
    if not target.is_file():
        logger.error(f"Profiling target is not a file: {target}")
        raise typer.Exit(code=1)
    if not os.access(target, os.X_OK):
        logger.error(f"Profiling target is not executable: {target}")
        raise typer.Exit(code=1)

    path_recording = output_path / "perf.data"
    path_processed = output_path / "perf.processed"
    path_folded = output_path / "perf.folded"
    path_svg = output_path / "flamegraph.svg"
    result_files = [path_recording, path_processed, path_folded, path_svg]
    for file in result_files:
        if file.exists():
            if not force:
                logger.error(f"Output file already exists: {file}")
                raise typer.Exit(code=1)
            file.unlink()

    output_path.mkdir(parents=True, exist_ok=True)
    cmd = [
        path_perf,
        "record",
        f"--freq={frequency}",
        "-g",
        f"--output={path_recording}",
        "--",
        str(target),
    ] + arguments

    try:
        process = subprocess.Popen(cmd)
        process.wait()
    except KeyboardInterrupt:
        process.wait()

    cmd = ["perf", "script", f"--input={path_recording}"]
    path_processed.write_text(subprocess.check_output(cmd, text=True))

    cmd = ["stackcollapse-perf.pl", str(path_processed)]
    path_folded.write_text(subprocess.check_output(cmd, text=True))

    cmd = ["flamegraph.pl", str(path_folded)]
    path_svg.write_text(subprocess.check_output(cmd, text=True))


if __name__ == "__main__":
    app()
