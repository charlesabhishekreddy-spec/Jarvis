from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from jarvis.core.config import load_settings
from jarvis.core.logging import configure_logging
from jarvis.core.runtime import JarvisRuntime
from jarvis.system_control.startup import StartupManager


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the JARVIS runtime.")
    parser.add_argument("--config", default=None, help="Optional path to a YAML settings file.")
    parser.add_argument("--api", action="store_true", help="Start the FastAPI service.")
    parser.add_argument("--host", default=None, help="Override API host.")
    parser.add_argument("--port", type=int, default=None, help="Override API port.")
    parser.add_argument("--once", default=None, help="Execute a single command and exit.")
    parser.add_argument("--startup-status", action="store_true", help="Show startup registration status.")
    parser.add_argument("--install-startup", action="store_true", help="Register JARVIS to start at user login.")
    parser.add_argument("--uninstall-startup", action="store_true", help="Remove the startup registration.")
    parser.add_argument(
        "--startup-mode",
        choices=("api", "background"),
        default=None,
        help="Startup mode to use with startup registration commands.",
    )
    args = parser.parse_args()

    settings = load_settings(args.config)
    log_path = str(Path(settings.runtime.data_dir) / "jarvis.log")
    configure_logging(log_path)

    if args.startup_status or args.install_startup or args.uninstall_startup:
        asyncio.run(_manage_startup(settings, args))
        return

    if args.once:
        asyncio.run(_run_once(settings, args.once))
        return

    if args.api or settings.runtime.auto_start_api:
        from jarvis.api.app import create_app

        try:
            import uvicorn
        except ImportError as exc:  # pragma: no cover
            raise SystemExit("uvicorn is not installed. Install requirements.txt to run the API server.") from exc

        app = create_app(args.config)
        host = args.host or settings.runtime.host
        port = args.port or settings.runtime.port
        uvicorn.run(app, host=host, port=port)
        return

    asyncio.run(_run_forever(settings))


async def _run_once(settings, command_text: str) -> None:
    runtime = JarvisRuntime(settings)
    await runtime.start()
    try:
        response = await runtime.execute_text(command_text, source="cli")
        print(response.message)
    finally:
        await runtime.stop()


async def _manage_startup(settings, args) -> None:
    manager = StartupManager(settings)
    if args.install_startup:
        result = await manager.install(mode=args.startup_mode, host=args.host, port=args.port, config_path=args.config)
    elif args.uninstall_startup:
        result = await manager.uninstall()
    else:
        result = await manager.status(mode=args.startup_mode, host=args.host, port=args.port, config_path=args.config)
    print(json.dumps(result, indent=2))


async def _run_forever(settings) -> None:
    runtime = JarvisRuntime(settings)
    await runtime.start()
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        await runtime.stop()


if __name__ == "__main__":
    main()
