import { initDatabase } from './database/sqliteManager';
import authService from './authService';
import notificationService from './notificationService';
import offlineSyncService from './offlineSyncService';
import websocketService from './websocketService';

export const initializeApp = async (): Promise<void> => {
  try {
    // Initialize SQLite database for offline storage
    await initDatabase();

    // Initialize notification service
    notificationService.initialize();

    // Initialize offline sync service
    await offlineSyncService.initialize();

    // Check if user is already authenticated
    const isAuthenticated = await authService.isAuthenticated();

    // Initialize WebSocket if authenticated
    if (isAuthenticated) {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
      const wsUrl = backendUrl.replace(/^http/, 'ws');
      try {
        await websocketService.connect(`${wsUrl}/ws`);
      } catch (error) {
        console.warn('Failed to connect WebSocket:', error);
      }
    }

    // Request notification permissions if enabled
    if (process.env.REACT_APP_ENABLE_PUSH_NOTIFICATIONS === 'true') {
      await notificationService.requestPermissions();
    }

    // Initialize analytics
    if (process.env.REACT_APP_SENTRY_DSN) {
      // await initializeSentry(process.env.REACT_APP_SENTRY_DSN);
    }

    console.log('App initialization completed');
  } catch (error) {
    console.error('App initialization error:', error);
    throw error;
  }
};
