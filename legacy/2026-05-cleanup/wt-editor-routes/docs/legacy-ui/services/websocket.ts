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
  data: any;
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
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.isConnected = true;
          this.reconnectCount = 0;
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
          console.log('WebSocket disconnected');
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
    if (this.reconnectCount < this.reconnectAttempts) {
      const delay = this.reconnectInterval * Math.pow(2, this.reconnectCount);
      console.log(`Reconnecting in ${delay}ms... (attempt ${this.reconnectCount + 1})`);

      setTimeout(() => {
        this.reconnectCount++;
        this.connect().catch((error) => {
          console.error('Reconnection failed:', error);
          this.attemptReconnect();
        });
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
    }
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
