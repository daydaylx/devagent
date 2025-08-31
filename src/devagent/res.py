from __future__ import annotations
import importlib.resources as ir

def read_template(name: str) -> str:
    """
    Lies eine Textvorlage aus devagent/templates/<name>.
    Funktioniert sowohl aus dem Source-Tree als auch aus site-packages.
    """
    with ir.files("devagent").joinpath(f"templates/{name}").open("r", encoding="utf-8") as f:
        return f.read()
