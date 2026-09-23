# Embeddster Web GUI

Browser-based monitor for the embedded systems lab. Students edit `ProtocolHandler` in Python (runs via Pyodide), connect the board over Web Serial, and view station tilt in 3D.

## Requirements (students)

- Chrome or Edge (Web Serial)
- USB cable to the board
- No Python install required for the GUI

## Requirements (maintainers)

- Node.js 20+
- npm

## Run locally

```bash
cd web
npm install
npm run dev
```

Open the URL shown (localhost). Web Serial works on localhost without HTTPS.

## Build

```bash
npm run build
npm run preview
```

## Deploy

The app is a static Vite build. Deploy `web/` to Vercel or any static host.

## Protocol task

Implement `on_bytes` and `build_led_command` in the Protocol tab. The starter stub raises `NotImplementedError`. Use **Load .py** to run your file, then **Apply** if you edit it in the page.

Download your file for submission or local debugging:

```bash
python tools/protocol_harness.py protocol_handler.py --ascii "RXED: ..."
```

## Views

| Tab | Purpose |
|-----|---------|
| Main | 3D viewer, serial connect, LED commands, byte injector, charts |
| God Mode | Floating window over the main view: CAN sniffer, injection, loopback, random traffic |
| Protocol | Edit and reload Python handler |
