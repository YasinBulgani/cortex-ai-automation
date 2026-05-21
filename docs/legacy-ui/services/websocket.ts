/**
 * WebSocket Client Service
 * Handles real-time event streaming from backend
 */

export interface WebSocketClientConfig {
  url: string;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export interface TestEvent {
  type:
    | 'test_started'
    | 'test_passed'
    | 'test_failed'
    | 'test_skipped'
    | 'step_started'
    | 'step_passed'
    | 'step_failed'
    | 'screenshot'
    | 'log'
    | 'progress'
    | 'completed';
  timestamp: string;
  data: Record<string, unknown>;
}

export type EventCallback = (event: TestEvent) => void;

/**
 * WebSocket Client for real-time test monitoring
 */
export class WebSocketClient {
  private url: string;
  private reconnectAttempts: number;
  private reconnectInterval: number;
  private ws: WebSocket | null = null;
  private reconnectCount: number = 0;
  private eventListeners: Map<string, Set<EventCallback>> = new Map();
  private isConnected: boolean = false;
  private messageQueue: string[] = [];
  // Reconnect guard — ayni anda birden fazla reconnect zamanlayicisi/girisimi olusmasini engeller.
  // close -> attemptReconnect -> connect -> onerror -> attemptReconnect gibi cagri zincirlerinde
  // cift timer olusup duplicate WebSocket baglantilari kurulmasini onler.
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectInFlight: boolean = false;
  private manualDisconnect: boolean = false;

  constructor(config: WebSocketClientConfig) {
    this.url = config.url;
    this.reconnectAttempts = config.reconnectAttempts || 5;
    this.reconnectInterval = config.reconnectInterval || 3000;
  }

  /**
   * Connect to WebSocket server
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Yeni baglanti girisiminde onceki socket varsa temizle — duplicate baglanti engeli
        if (this.ws) {
          try { this.ws.close(); } catch { /* zaten kapali olabilir */ }
          this.ws = null;
        }
        this.manualDisconnect = false;
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.debug('WebSocket connected');
          this.isConnected = true;
          this.reconnectCount = 0;
          this.reconnectInFlight = false;
          this.flushMessageQueue();
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

        this.ws.onclose = () => {
          console.debug('WebSocket disconnected');
          this.isConnected = false;
          this.attemptReconnect();
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    // Manuel disconnect — otomatik reconnect tetiklenmesin
    this.manualDisconnect = true;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.reconnectInFlight = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }
  }

  /**
   * Subscribe to an event type
   */
  subscribe(eventType: string, callback: EventCallback): () => void {
    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, new Set());
    }

    this.eventListeners.get(eventType)!.add(callback);

    // Return unsubscribe function
    return () => {
      const listeners = this.eventListeners.get(eventType);
      if (listeners) {
        listeners.delete(callback);
      }
    };
  }

  /**
   * Subscribe to all events
   */
  subscribeAll(callback: EventCallback): () => void {
    return this.subscribe('*', callback);
  }

  /**
   * Handle incoming messages
   */
  private handleMessage(data: string): void {
    try {
      const event: TestEvent = JSON.parse(data);

      // Emit to specific event listeners
      const listeners = this.eventListeners.get(event.type);
      if (listeners) {
        listeners.forEach((callback) => callback(event));
      }

      // Emit to wildcard listeners
      const wildcardListeners = this.eventListeners.get('*');
      if (wildcardListeners) {
        wildcardListeners.forEach((callback) => callback(event));
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  /**
   * Send message to WebSocket server
   */
  send(message: any): void {
    const data = JSON.stringify(message);

    if (this.isConnected && this.ws) {
      this.ws.send(data);
    } else {
      // Queue message if not connected
      this.messageQueue.push(data);
    }
  }

  /**
   * Flush queued messages
   */
  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected && this.ws) {
      const message = this.messageQueue.shift();
      if (message) {
        this.ws.send(message);
      }
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    // Manuel disconnect sonrasi reconnect tetiklenmesin
    if (this.manualDisconnect) {
      return;
    }
    // Zaten bekleyen bir reconnect timer veya in-flight connect varsa tekrar basla verme.
    // Bu kontrol olmadan close -> onerror zinciri ayni anda iki timer olustururdu.
    if (this.reconnectTimer !== null || this.reconnectInFlight) {
      return;
    }
    if (this.reconnectCount >= this.reconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    const delay = this.reconnectInterval * Math.pow(2, this.reconnectCount);
    console.debug(`Reconnecting in ${delay}ms... (attempt ${this.reconnectCount + 1})`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectInFlight = true;
      this.reconnectCount++;
      this.connect()
        .catch((error) => {
          console.error('Reconnection failed:', error);
          this.reconnectInFlight = false;
          this.attemptReconnect();
        });
    }, delay);
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): boolean {
    return this.isConnected;
  }

  /**
   * Subscribe to test started events
   */
  onTestStarted(callback: EventCallback): () => void {
    return this.subscribe('test_started', callback);
  }

  /**
   * Subscribe to test passed events
   */
  onTestPassed(callback: EventCallback): () => void {
    return this.subscribe('test_passed', callback);
  }

  /**
   * Subscribe to test failed events
   */
  onTestFailed(callback: EventCallback): () => void {
    return this.subscribe('test_failed', callback);
  }

  /**
   * Subscribe to test skipped events
   */
  onTestSkipped(callback: EventCallback): () => void {
    return this.subscribe('test_skipped', callback);
  }

  /**
   * Subscribe to step started events
   */
  onStepStarted(callback: EventCallback): () => void {
    return this.subscribe('step_started', callback);
  }

  /**
   * Subscribe to step passed events
   */
  onStepPassed(callback: EventCallback): () => void {
    return this.subscribe('step_passed', callback);
  }

  /**
   * Subscribe to step failed events
   */
  onStepFailed(callback: EventCallback): () => void {
    return this.subscribe('step_failed', callback);
  }

  /**
   * Subscribe to screenshot events
   */
  onScreenshot(callback: EventCallback): () => void {
    return this.subscribe('screenshot', callback);
  }

  /**
   * Subscribe to log events
   */
  onLog(callback: EventCallback): () => void {
    return this.subscribe('log', callback);
  }

  /**
   * Subscribe to progress events
   */
  onProgress(callback: EventCallback): () => void {
    return this.subscribe('progress', callback);
  }

  /**
   * Subscribe to test run completion
   */
  onCompleted(callback: EventCallback): () => void {
    return this.subscribe('completed', callback);
  }

  /**
   * Wait for a specific event
   */
  waitForEvent(eventType: string, timeout: number = 30000): Promise<TestEvent> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        unsubscribe();
        reject(new Error(`Timeout waiting for event: ${eventType}`));
      }, timeout);

      const unsubscribe = this.subscribe(eventType, (event) => {
        clearTimeout(timer);
        unsubscribe();
        resolve(event);
      });
    });
  }
}

export default WebSocketClient;
