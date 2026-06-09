import '@testing-library/react-native/extend-expect';
import * as ReactNative from 'react-native';

// Mock React Native modules
jest.mock('react-native/Libraries/EventEmitter/NativeEventEmitter');
jest.mock('react-native-vector-icons/MaterialIcons', () => {
  return {
    __esModule: true,
    default: () => null,
  };
});

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

jest.mock('react-native-keychain', () => ({
  setGenericPassword: jest.fn(),
  getGenericPassword: jest.fn(),
  resetGenericPassword: jest.fn(),
}));

jest.mock('react-native-biometrics', () => {
  return jest.fn().mockImplementation(() => ({
    isSensorAvailable: jest.fn().mockResolvedValue({
      available: true,
      biometryType: 'Biometrics',
    }),
    simplePrompt: jest.fn().mockResolvedValue({ success: true }),
  }));
});

// Mock AsyncStorage
const mockAsyncStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};

jest.mock('@react-native-async-storage/async-storage', () => mockAsyncStorage);

// Mock NetInfo
jest.mock('@react-native-community/netinfo', () => ({
  fetch: jest.fn().mockResolvedValue({
    isConnected: true,
    type: 'wifi',
  }),
  addEventListener: jest.fn(),
}));

// Suppress console warnings in tests
global.console = {
  ...console,
  warn: jest.fn(),
  error: jest.fn(),
};
