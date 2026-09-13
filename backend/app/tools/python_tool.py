from pathlib import Path
import httpx
from app.core.config import get_settings
settings = get_settings()


def run_python(dataset_path: str, code: str, **_) -> dict:
    payload = {"dataset_file": Path(dataset_path).name, "code": code}
    try:
        with httpx.Client(timeout=settings.sandbox_timeout_seconds + 2) as client:
            response = client.post(f"{settings.sandbox_url.rstrip('/')}/run", json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok", False):
            raise RuntimeError(data.get("error", "Sandbox 执行失败"))
        return data
    except httpx.HTTPError as e:
        raise RuntimeError(f"Python Sandbox 调用失败: {e}") from e
