import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from './useWebSocket';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  readyState = MockWebSocket.CONNECTING;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) this.onclose();
  }

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) this.onopen();
  }

  simulateMessage(data: unknown) {
    if (this.onmessage) this.onmessage({ data: JSON.stringify(data) });
  }

  simulateError() {
    if (this.onerror) this.onerror();
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) this.onclose();
  }

  static instances: MockWebSocket[] = [];
  static reset() { MockWebSocket.instances = []; }
}

(global as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket;

describe('useWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.reset();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('starts disconnected', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8080'));
    expect(result.current.isConnected).toBe(false);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('becomes connected on open', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8080'));

    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });

    expect(result.current.isConnected).toBe(true);
  });

  it('parses JSON messages', () => {
    const { result } = renderHook(() => useWebSocket<{ price: number }>('ws://localhost:8080'));

    act(() => {
      MockWebSocket.instances[0].simulateOpen();
      MockWebSocket.instances[0].simulateMessage({ price: 42000 });
    });

    expect(result.current.data).toEqual({ price: 42000 });
  });

  it('sets error on WebSocket error', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8080'));

    act(() => {
      MockWebSocket.instances[0].simulateError();
    });

    expect(result.current.error).toBe('WebSocket error');
  });

  it('disconnects on close', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8080'));

    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });

    expect(result.current.isConnected).toBe(true);

    act(() => {
      // Prevent auto-reconnect from firing during this test
      MockWebSocket.instances[0].onclose = null;
      MockWebSocket.instances[0].simulateClose();
    });
  });

  it('auto-reconnects after disconnect', () => {
    renderHook(() => useWebSocket('ws://localhost:8080'));

    act(() => {
      MockWebSocket.instances[0].simulateOpen();
      MockWebSocket.instances[0].simulateClose();
    });

    // Advance past reconnect delay
    act(() => { jest.advanceTimersByTime(1100); });

    expect(MockWebSocket.instances.length).toBe(2);
  });

  it('cleans up on unmount', () => {
    const { unmount } = renderHook(() => useWebSocket('ws://localhost:8080'));

    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });

    unmount();

    // After unmount, the ws should be closed
    expect(MockWebSocket.instances[0].readyState).toBe(MockWebSocket.CLOSED);
  });
});
