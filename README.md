# Embeddster: Embedded Systems Testing Platform

## Overview

Embeddster is a platform for the **25.27 - Sistemas Embebidos** course at ITBA (Instituto Tecnológico de Buenos Aires), using an ESP32 to test and assist with TPs. It connects to TP hardware via a custom PCB and interfaces with a PC GUI for testing, development, and evaluation.

## Key Features
- **Hardware Interface**: Custom PCB (KiCad: `hw/kicad/`) connects ESP32 to TP peripherals (encoder, display, CAN, ...).
- **ESP32 Firmware**: (PlatformIO: `fw/`) Manages I/O, protocols (UART, SPI, CAN), and PC communication.
- **PC GUI**: Python-based (`gui/`) for simulating inputs, monitoring outputs, and visualizing data.
- **TP Support**:
  - **TP1**: Tests TP1 board (displays, encoder, LEDs)
  - **TP2**: Visualizes CAN messages and sends custom messages; based on [canmon](https://github.com/alheir/canmon).
  - **TP3**: Generates/analyzes FSK signals, ADC/DAC testing.

## License
MIT License (see `LICENSE`).

## Acknowledgments
- Inspired by ITBA 25.27 course TPs (TP1: Interruptions, TP2: Serial Comm, TP3: FSK Modem).
- Special thanks to the **Sistemas Embebidos** chair, led by Daniel Andres Jacoby, Nicolas Magliola, and Matías Bergerman, for their detailed TP specifications and support.