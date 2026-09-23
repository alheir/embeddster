#!/usr/bin/env python3
"""
Local ProtocolHandler test harness (stdlib only, no GUI).

Usage:
  python tools/protocol_harness.py path/to/protocol_handler.py
  python tools/protocol_harness.py path/to/protocol_handler.py --hex "52 2d 31 30 0a"
  python tools/protocol_harness.py path/to/protocol_handler.py --ascii "RXED: ..."

Set breakpoints in protocol_handler.py and run under a debugger.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType


def _write_station_module(target: Path, station_count: int) -> None:
    ids = ", ".join(f'b"{i}"' for i in range(station_count))
    names = ", ".join(f'"0x{0x100 + i:03X}"' for i in range(station_count))
    target.write_text(
        f"""STATION_ID = [{ids}]
STATION_ID_NAMES = [{names}]
STATION_ANGLES = [b"R", b"C", b"O"]
STATION_ANGLES_COUNT = len(STATION_ANGLES)
STATION_COUNT = len(STATION_ID)
""",
        encoding="utf-8",
    )


def _load_handler(handler_path: Path, station_count: int) -> ModuleType:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_dir = root / "src" / "package"
        protocol_dir = root / "src" / "protocol"
        package_dir.mkdir(parents=True)
        protocol_dir.mkdir(parents=True)
        (root / "src" / "__init__.py").write_text("", encoding="utf-8")
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
        (protocol_dir / "__init__.py").write_text("", encoding="utf-8")
        _write_station_module(package_dir / "Station.py", station_count)
        (protocol_dir / "protocol_handler.py").write_text(
            handler_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        sys.path.insert(0, str(root))
        spec = importlib.util.spec_from_file_location(
            "src.protocol.protocol_handler",
            protocol_dir / "protocol_handler.py",
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load protocol_handler module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def _parse_payload(args: argparse.Namespace) -> bytes:
    if args.hex:
        return bytes(int(b, 16) for b in args.hex.split())
    if args.ascii is not None:
        text = args.ascii
        if not text.endswith("\n"):
            text += "\n"
        return text.encode("utf-8")
    return sys.stdin.buffer.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Test ProtocolHandler locally")
    parser.add_argument("handler", type=Path, help="Path to protocol_handler.py")
    parser.add_argument("--stations", type=int, default=7, help="STATION_COUNT (default: 7)")
    parser.add_argument("--hex", help="Input bytes as hex (space separated)")
    parser.add_argument("--ascii", help="Input bytes as ASCII string")
    parser.add_argument(
        "--led",
        nargs=4,
        metavar=("STATION", "R", "G", "B"),
        help="Call build_led_command instead of on_bytes",
    )
    args = parser.parse_args()

    if not args.handler.is_file():
        print(f"File not found: {args.handler}", file=sys.stderr)
        return 1

    module = _load_handler(args.handler, args.stations)
    handler = module.ProtocolHandler()

    if args.led:
        station, r, g, b = args.led
        out = handler.build_led_command(int(station), bool(int(r)), bool(int(g)), bool(int(b)))
        print(out)
        return 0

    payload = _parse_payload(args)
    messages = handler.on_bytes(payload)
    print(messages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
