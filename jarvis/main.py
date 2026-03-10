from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import uvicorn

from jarvis.api.app import create_app
from jarvis.core.config import load_settings
from jarvis.core.logging import configure_logging
from jarvis.core.runtime import JarvisRuntime


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the JARVIS runtime.")
    parser.add_argument("--config", default=None, help="Optional path to a YAML settings file.")
    parser.add_argument("--api", action="store_true", help="Start the FastAPI service.")
    parser.add_argument("--host", default=None, help="Override API host.")
    parser.add_argument("--port", type=int, default=None, help="Override API port.")
    parser.add_argument("--once", default=None, help="Execute a single command and exit.")
    args = parser.parse_args()

    settings = load_settings(args.config)
    log_path = str(Path(settings.runtime.data_dir) / "jarvis.log")
    configure_logging(log_path)

    if args.once:
        asyncio.run(_run_once(settings, args.once))
        return

    app = create_app(args.config)
    host = args.host or settings.runtime.host
    port = args.port or settings.runtime.port
    uvicorn.run(app, host=host, port=port)


async def _run_once(settings, command_text: str) -> None:
    runtime = JarvisRuntime(settings)
    await runtime.start()
    try:
        response = await runtime.execute_text(command_text, source="cli")
        print(response.message)
    finally:
        await runtime.stop()


if __name__ == "__main__":
    main()
