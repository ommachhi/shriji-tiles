from __future__ import annotations

import os

import uvicorn

from runtime_paths import get_backend_base_dir


def main() -> int:
    base_dir = get_backend_base_dir()
    os.chdir(base_dir)

    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("BACKEND_PORT", "8000"))
    log_level = os.environ.get("BACKEND_LOG_LEVEL", "info")

    print(f"Starting Product Catalog backend from {base_dir}", flush=True)

    from main import app

    uvicorn.run(app, host=host, port=port, log_level=log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
