export class SerialConnection {
  private port: SerialPort | null = null;
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
  private reading = false;

  get isConnected(): boolean {
    return this.port !== null;
  }

  static isSupported(): boolean {
    return 'serial' in navigator;
  }

  async connect(baudRate: number, onData: (chunk: Uint8Array) => void): Promise<void> {
    if (!SerialConnection.isSupported()) {
      throw new Error('Web Serial is not supported. Use Chrome or Edge.');
    }

    this.port = await navigator.serial.requestPort();
    await this.port.open({ baudRate });

    if (!this.port.readable || !this.port.writable) {
      throw new Error('Serial port streams are unavailable');
    }

    this.reader = this.port.readable.getReader();
    this.writer = this.port.writable.getWriter();
    this.reading = true;
    this.readLoop(onData);
  }

  private async readLoop(onData: (chunk: Uint8Array) => void) {
    while (this.reading && this.reader) {
      try {
        const { value, done } = await this.reader.read();
        if (done) break;
        if (value?.length) onData(value);
      } catch {
        break;
      }
    }
  }

  async write(data: Uint8Array): Promise<void> {
    if (!this.writer) throw new Error('Not connected');
    await this.writer.write(data);
  }

  async writeText(text: string): Promise<void> {
    await this.write(new TextEncoder().encode(text));
  }

  async disconnect(): Promise<void> {
    this.reading = false;
    try {
      await this.reader?.cancel();
    } catch {
      // ignore
    }
    try {
      await this.reader?.releaseLock();
    } catch {
      // ignore
    }
    try {
      await this.writer?.close();
    } catch {
      // ignore
    }
    try {
      await this.port?.close();
    } catch {
      // ignore
    }
    this.reader = null;
    this.writer = null;
    this.port = null;
  }
}
