import { useEffect, useState } from 'react';
import * as SecureStore from 'expo-secure-store';
import authService from '@services/authService';

interface AppStoreState {
  isInitialized: boolean;
  isAuthenticated: boolean;
  user: any | null;
}

export const useAppStore = (): AppStoreState => {
  const [state, setState] = useState<AppStoreState>({
    isInitialized: false,
    isAuthenticated: false,
    user: null,
  });

  useEffect(() => {
    const initialize = async () => {
      try {
        const isAuth = await authService.isAuthenticated();
        const user = await authService.getCurrentUser();

        setState({
          isInitialized: true,
          isAuthenticated: isAuth,
          user,
        });
      } catch (error) {
        console.error('Failed to initialize app store:', error);
        setState(prev => ({
          ...prev,
          isInitialized: true,
        }));
      }
    };

    initialize();
  }, []);

  return state;
};
