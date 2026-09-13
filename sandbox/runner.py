from __future__ import annotations
import ast
import contextlib
import io
import json
import math
import multiprocessing as mp
import os
import statistics
from pathlib import Path
import numpy as np
import pandas as pd

ALLOWED_IMPORTS = {"pandas", "numpy", "math", "statistics"}
BANNED_NAMES = {
    "open", "eval", "exec", "compile", "__import__", "input", "help",
    "breakpoint", "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "os", "sys", "subprocess", "socket", "pathlib", "shutil", "requests", "httpx",
}


def validate_code(code: str) -> None:
    if len(code) > 12000:
        raise ValueError("代码过长")
    tree = ast.parse(code, mode="exec")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    raise ValueError(f"禁止导入: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if not node.module or node.module.split(".")[0] not in ALLOWED_IMPORTS:
                raise ValueError(f"禁止导入: {node.module}")
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            raise ValueError(f"禁止名称: {node.id}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("禁止访问双下划线属性")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            raise ValueError("禁止 global/nonlocal")


def _load(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        for enc in ("utf-8-sig", "utf-8", "gb18030", "latin1"):
            try: return pd.read_csv(path, encoding=enc)
            except UnicodeDecodeError: pass
        return pd.read_csv(path)
    return pd.read_excel(path)


def _serialize(obj):
    if isinstance(obj, pd.DataFrame):
        return {"type": "dataframe", "columns": list(map(str, obj.columns)), "records": obj.head(200).replace({np.nan: None}).to_dict("records")}
    if isinstance(obj, pd.Series):
        return {"type": "series", "data": obj.head(200).replace({np.nan: None}).to_dict()}
    if isinstance(obj, np.ndarray):
        return obj[:200].tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    try:
        json.dumps(obj, default=str)
        return obj
    except Exception:
        return str(obj)


def _worker(dataset_path: str, code: str, queue: mp.Queue):
    try:
        validate_code(code)
        df = _load(Path(dataset_path))
        safe_builtins = {
            "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict, "enumerate": enumerate,
            "float": float, "int": int, "len": len, "list": list, "max": max, "min": min,
            "range": range, "round": round, "set": set, "sorted": sorted, "str": str,
            "sum": sum, "tuple": tuple, "zip": zip, "print": print,
        }
        globals_dict = {"__builtins__": safe_builtins, "pd": pd, "np": np, "math": math, "statistics": statistics}
        locals_dict = {"df": df.copy(), "result": None}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(compile(code, "<sandbox>", "exec"), globals_dict, locals_dict)
        queue.put({"ok": True, "result": _serialize(locals_dict.get("result")), "stdout": buf.getvalue()[-4000:]})
    except Exception as e:
        queue.put({"ok": False, "error": f"{type(e).__name__}: {e}"})


def run_safely(dataset_file: str, code: str, timeout: int = 8) -> dict:
    root = Path(os.getenv("DATA_ROOT", "/data")).resolve()
    path = (root / Path(dataset_file).name).resolve()
    if root not in path.parents or not path.exists():
        raise ValueError("数据文件不存在或路径非法")
    queue: mp.Queue = mp.Queue(maxsize=1)
    proc = mp.Process(target=_worker, args=(str(path), code, queue), daemon=True)
    proc.start(); proc.join(timeout)
    if proc.is_alive():
        proc.terminate(); proc.join(1)
        return {"ok": False, "error": f"执行超时（>{timeout}s）"}
    return queue.get_nowait() if not queue.empty() else {"ok": False, "error": "Sandbox 未返回结果"}
