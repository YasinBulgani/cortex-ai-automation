import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Provider as ReduxProvider } from 'react-redux';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import * as SecureStore from 'expo-secure-store';
import { RootNavigator } from '@navigation/RootNavigator';
import { initializeApp } from '@services/appInitializer';
import { store } from '@store/index';
import { useAppStore } from '@hooks/useAppStore';
import SplashScreen from '@screens/SplashScreen';

const Stack = createNativeStackNavigator();
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 1000 * 60 * 5 }, // 5 minutes
    mutations: { retry: 1 },
  },
});

const AppContent: React.FC = () => {
  const { isInitialized, isAuthenticated } = useAppStore();

  useEffect(() => {
    const bootstrap = async () => {
      try {
        await initializeApp();
      } catch (error) {
        console.error('App initialization failed:', error);
      }
    };

    bootstrap();
  }, []);

  if (!isInitialized) {
    return <SplashScreen />;
  }

  return (
    <NavigationContainer>
      <RootNavigator isAuthenticated={isAuthenticated} />
    </NavigationContainer>
  );
};

const App: React.FC = () => {
  return (
    <ReduxProvider store={store}>
      <QueryClientProvider client={queryClient}>
        <AppContent />
      </QueryClientProvider>
    </ReduxProvider>
  );
};

export default App;
