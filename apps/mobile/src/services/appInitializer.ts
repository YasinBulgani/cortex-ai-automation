import { initDatabase } from './database/sqliteManager';
import authService from './authService';

export const initializeApp = async (): Promise<void> => {
  try {
    // Initialize SQLite database for offline storage
    await initDatabase();

    // Check if user is already authenticated
    const isAuthenticated = await authService.isAuthenticated();

    // Initialize push notifications if enabled
    if (process.env.REACT_APP_ENABLE_PUSH_NOTIFICATIONS === 'true') {
      // await initializePushNotifications();
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
