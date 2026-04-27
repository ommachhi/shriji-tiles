from __future__ import annotations

from main import (
    _catalog_sources_signature,
    _save_runtime_catalog_cache,
    load_catalogs,
)


def main() -> None:
    source_store = load_catalogs()
    signature = _catalog_sources_signature()
    _save_runtime_catalog_cache(source_store, signature)
    print(f"[build-runtime-cache] wrote cache for {len(source_store)} catalogs")


if __name__ == "__main__":
    main()