from __future__ import annotations

import zipfile
from pathlib import Path

# Shell launchers must stay executable after unzipping on macOS / Linux.
EXECUTABLE_SUFFIXES = {".command", ".sh"}


def write_project(root: Path, files: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        # newline="" writes line endings exactly as given: Start.command breaks with Windows CRLF.
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(content)


def zip_project(project_dir: Path, zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(project_dir.rglob("*")):
            if not file_path.is_file():
                continue
            info = zipfile.ZipInfo.from_file(file_path, file_path.relative_to(project_dir).as_posix())
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if file_path.suffix in EXECUTABLE_SUFFIXES else 0o644
            info.external_attr = (0o100000 | mode) << 16
            archive.writestr(info, file_path.read_bytes())
    return zip_path
