import os
import pathlib


def data_path(name: str) -> str:
    here = pathlib.Path(__file__).parent
    # Use repo root samples if present; else the tests/fixtures folder
    candidates = [
        here.parent.parent / name,                 # repo root (../../name)
        here / "fixtures" / name,
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    raise FileNotFoundError(name)
