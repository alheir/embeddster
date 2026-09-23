# Embeddster firmware (Zephyr)

Experimental Zephyr port of the Embeddster ESP32 firmware. The supported course firmware remains in [`fw/`](../fw/) (PlatformIO / Arduino).

Current scope: boot on ESP32 DOIT DevKit V1, MCP2515 over SPI3, loopback self-test, then CAN sniffer with `RXED:` lines compatible with the GUI serial parser.

## Hardware

| Signal | GPIO |
|--------|------|
| SPI MOSI / MISO / SCK | 23 / 19 / 18 (VSPI / SPI3) |
| MCP2515 CS / INT | 5 / 17 |
| Onboard LED | 2 |
| UART | 115200 8N1 |

CAN: 125 kbit/s, 16 MHz oscillator (same as the PlatformIO firmware).

## Prerequisites

- Git, CMake 3.20+, [uv](https://docs.astral.sh/uv/)
- [Zephyr SDK 1.0.1](https://github.com/zephyrproject-rtos/sdk-ng/releases/tag/v1.0.1) with `xtensa-espressif_esp32_zephyr-elf`
- USB serial driver for the ESP32

Host Python tools are pinned in `pyproject.toml` / `uv.lock`. Zephyr and its modules are pinned in `west.yml` (v4.4.2). Neither is committed; each machine downloads them once.

## One-time setup

From the repository root, substitute `<repo>` with your checkout directory name.

```bash
cd fw-zephyr
uv sync
```

West workspace (creates `.west/`, `zephyr/`, `modules/` in the **parent** of the checkout):

```bash
cd ..
uv --directory <repo>/fw-zephyr run west init -l <repo> --mf fw-zephyr/west.yml
cd <repo>
uv run --project fw-zephyr west update
uv run --project fw-zephyr west blobs fetch hal_espressif
```

Zephyr SDK (minimal bundle + ESP32 toolchain only). Pick the archive for your OS from the [SDK release](https://github.com/zephyrproject-rtos/sdk-ng/releases/tag/v1.0.1), extract it, then:

**Linux / macOS**

```bash
cd zephyr-sdk-1.0.1
./setup.sh -t xtensa-espressif_esp32_zephyr-elf -c
export ZEPHYR_SDK_INSTALL_DIR="$PWD"
```

**Windows** (requires `7z` on `PATH`)

```powershell
cd zephyr-sdk-1.0.1
.\setup.cmd /t xtensa-espressif_esp32_zephyr-elf /c
$env:ZEPHYR_SDK_INSTALL_DIR = "$PWD"
```

## Build, flash, monitor

From the repository root:

```bash
export ZEPHYR_SDK_INSTALL_DIR=/path/to/zephyr-sdk-1.0.1   # or set in the shell profile
uv run --project fw-zephyr west build -b esp32_devkitc/esp32/procpu -p always fw-zephyr
uv run --project fw-zephyr west flash --esp-device <serial-port>
uv run --project fw-zephyr west espressif monitor -p <serial-port> -b 115200
```

On Windows use `$env:ZEPHYR_SDK_INSTALL_DIR` and a `COMx` port name.

## Expected output

```
~~~~ Embeddster Zephyr CAN spike ~~~~
...
Loopback self-test OK
RXED: ID=0x100 Data=0x522D3130='R-10' Len=4
Listening on CAN bus (125 kbit/s)...
```

## Roadmap

1. Serial command parser (`M1`, `M2`, `MODE_*`, `SEND_*`, `LED_*`)
2. Sniffer and random-send modes
3. Retry on send failure
4. WS2812 (`led_strip`, GPIO21)
5. 74HC595 shift registers (status LEDs, TP1 board)
