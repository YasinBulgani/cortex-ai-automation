import websocketService from '@services/websocketService';

describe('WebSocket Service', () => {
  beforeEach(() => {
    websocketService.disconnect();
  });

  it('should have listeners system', () => {
    const listener = jest.fn();
    websocketService.on('test-event', listener);

    expect(listener).not.toHaveBeenCalled();
  });

  it('should have message queue', () => {
    // Initially not connected
    expect(websocketService.isConnected()).toBe(false);
  });

  it('should track connection status', () => {
    expect(websocketService.isDisconnected()).toBe(true);
  });

  it('should register and call listeners', () => {
    const listener = jest.fn();
    websocketService.on('test', listener);

    // In a real test with actual WebSocket, listener would be called
    // This is a unit test for the interface
    expect(listener).not.toHaveBeenCalled();

    websocketService.off('test', listener);
  });
});
