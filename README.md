# Embeddster: Plataforma de Pruebas para Sistemas Embebidos

## Resumen

Embeddster es una plataforma para el curso **25.27 - Sistemas Embebidos** en ITBA (Instituto Tecnológico de Buenos Aires), que utiliza un ESP32 para probar y asistir con los trabajos prácticos (TPs). Se conecta al hardware de los TPs a través de un PCB personalizado y se vincula con una GUI en PC para pruebas, desarrollo y evaluación.

## Características Principales
- **Interfaz de Hardware**: PCB custom (KiCad: `hw/kicad/`) que conecta el ESP32 a periféricos de los TPs (encoder, display, CAN).
- **Firmware del ESP32**: (PlatformIO: `fw/`) Gestiona I/O, protocolos (UART, SPI, CAN) y comunicación con PC.
- **GUI en PC**: Basada en Python (`gui/`) para simular entradas, monitorear salidas y visualizar datos.
- **Soporte para TPs**:
  - **TP1**: Prueba la placa TP1 (displays, encoder, LEDs).
  - **TP2**: Visualiza mensajes CAN y envía mensajes personalizados; basado en [canmon](https://github.com/alheir/canmon); extensión de [TiltNetworkTool](https://github.com/alheir/TiltNetworkTool).

## Getting Started

### PCB Solo (Sin GUI)
En este modo, el ESP32 opera de forma autónoma a través de comandos seriales enviados desde una terminal. El ESP32 inicia en modo sniffer por defecto.

- **Modo Sniffer (M1)**: Enviar `M1\n` por serial para activar. El ESP32 escucha mensajes CAN entrantes y los reenvía por serial. Útil para monitorear tráfico CAN sin intervención. Se indica activo con un LED azul. El formato por serial es:
```bash
RXED: ID=0x{id} Data=0x{data}='{ascii}' Len={len}\n
```
- **Modo Random Send (M2)**: Enviar `M2\n` por serial para activar. El ESP32 genera y envía mensajes CAN aleatorios (ángulos simulados) al bus, simulando estaciones remotas. Se indica activo con un LED verde.
  
### 

### Con GUI

En el directorio el proyecto, crear entorno virtual

```bash
python -m venv venv
```

Activar el entorno virtual:

- En Windows:
    ```bash
    venv\Scripts\activate
    ```
- En Linux/Mac:
    ```bash
    source venv/bin/activate
    ```

Instalar dependencias

```bash
pip install -r requirements.txt
```

Ejecutar la aplicación

```bash
python main.py
```

- **Operación Normal**: Conectar el puerto serial en la GUI. Recibe mensajes CAN del ESP32 (procesados por [`ProtocolHandler`](gui/src/protocol/protocol_handler.py)), actualiza modelos 3D de estaciones y permite enviar comandos LED RGB a estaciones específicas.
  
![alt text](docs/gui_main.png)

- `God Mode`: Abrir desde el menú de acciones de la GUI (requiere conexión real, no emulador). Permite monitoreo avanzado de CAN, inyección de mensajes personalizados, control de modos CAN (NORMAL/LOOPBACK) y envío de comandos LED. Al cerrar `God Mode`, el ESP32 se resetea automáticamente a NORMAL y sniffer (M1).

![alt text](docs/gui_god_mode.png)

## Licencia
Licencia MIT (ver `LICENSE`).
