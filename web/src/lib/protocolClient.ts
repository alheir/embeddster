import type { ParsedMessage, ProtocolCallResult } from '../types';

type WorkerResponse = {
  id: number;
  ok: boolean;
  messages?: ParsedMessage[];
  bytes?: number[];
  logs?: string[];
  error?: string | null;
};

let nextId = 1;

export class ProtocolClient {
  private worker: Worker;
  private ready = false;
  private pending = new Map<number, { resolve: (v: WorkerResponse) => void; reject: (e: Error) => void }>();

  constructor() {
    this.worker = new Worker(new URL('../workers/pyodide.worker.ts', import.meta.url), {
      type: 'module',
    });
    this.worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
      const { id } = event.data;
      const entry = this.pending.get(id);
      if (!entry) return;
      this.pending.delete(id);
      entry.resolve(event.data);
    };
    this.worker.onerror = (event) => {
      for (const [, entry] of this.pending) {
        entry.reject(new Error(event.message));
      }
      this.pending.clear();
    };
  }

  private call(type: string, payload: unknown): Promise<WorkerResponse> {
    const id = nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.worker.postMessage({ id, type, payload });
    });
  }

  async init(stationCount: number, protocolCode: string): Promise<string[]> {
    this.ready = false;
    const res = await this.call('init', { stationCount, protocolCode });
    if (!res.ok) throw new Error(res.error ?? 'Failed to init protocol worker');
    this.ready = true;
    return res.logs ?? [];
  }

  async onBytes(data: Uint8Array): Promise<ProtocolCallResult> {
    if (!this.ready) {
      return { messages: [], logs: [], error: 'Protocol worker not initialized' };
    }
    const res = await this.call('on_bytes', { data });
    return {
      messages: res.messages ?? [],
      logs: res.logs ?? [],
      error: res.ok ? null : (res.error ?? 'on_bytes failed'),
    };
  }

  async buildLedCommand(
    stationIndex: number,
    r: boolean,
    g: boolean,
    b: boolean,
  ): Promise<{ bytes: Uint8Array; logs: string[]; error: string | null }> {
    if (!this.ready) {
      return { bytes: new Uint8Array(), logs: [], error: 'Protocol worker not initialized' };
    }
    const res = await this.call('build_led_command', { stationIndex, r, g, b });
    return {
      bytes: new Uint8Array(res.bytes ?? []),
      logs: res.logs ?? [],
      error: res.ok ? null : (res.error ?? 'build_led_command failed'),
    };
  }

  dispose() {
    this.worker.terminate();
    this.pending.clear();
    this.ready = false;
  }
}
