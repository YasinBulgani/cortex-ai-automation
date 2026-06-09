import * as SecureStore from 'expo-secure-store';
import * as WebBrowser from 'expo-web-browser';
import * as AuthSession from 'expo-auth-session';
import ReactNativeBiometrics from 'react-native-biometrics';
import apiClient from './apiClient';

interface LoginCredentials {
  email: string;
  password: string;
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: string;
    email: string;
    name: string;
    org_id: string;
  };
}

interface BiometricData {
  available: boolean;
  biometryType: string;
}

class AuthService {
  private static instance: AuthService;

  private constructor() {}

  static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/login', credentials);

    await Promise.all([
      SecureStore.setItemAsync('access_token', response.data.access_token),
      SecureStore.setItemAsync('refresh_token', response.data.refresh_token),
      SecureStore.setItemAsync('user', JSON.stringify(response.data.user)),
    ]);

    return response.data;
  }

  async loginWithOAuth(): Promise<AuthResponse> {
    const discovery = await AuthSession.fetchDiscoveryAsync(
      process.env.REACT_APP_OAUTH_ISSUER || 'https://auth.neurex.com',
    );

    const authRequest = new AuthSession.AuthRequest({
      clientId: process.env.REACT_APP_OAUTH_CLIENT_ID || 'neurex_mobile',
      redirectUrl: AuthSession.makeRedirectUri({
        scheme: 'neurex',
      }),
      scopes: ['openid', 'profile', 'email', 'offline_access'],
      usePKCE: true,
    });

    const result = await authRequest.promptAsync(discovery);

    if (result.type !== 'success') {
      throw new Error('OAuth login failed');
    }

    // Exchange code for tokens
    const tokenResponse = await apiClient.post<AuthResponse>('/auth/oauth/callback', {
      code: result.params.code,
      code_verifier: authRequest.codeVerifier,
    });

    await Promise.all([
      SecureStore.setItemAsync('access_token', tokenResponse.data.access_token),
      SecureStore.setItemAsync('refresh_token', tokenResponse.data.refresh_token),
      SecureStore.setItemAsync('user', JSON.stringify(tokenResponse.data.user)),
    ]);

    return tokenResponse.data;
  }

  async loginWithBiometrics(): Promise<AuthResponse> {
    try {
      const biometrics = await this.checkBiometricAvailability();
      if (!biometrics.available) {
        throw new Error('Biometric authentication not available');
      }

      const rnBiometrics = new ReactNativeBiometrics();
      const { success } = await rnBiometrics.simplePrompt({
        promptMessage: 'Authenticate with Neurex',
        fallbackPromptMessage: 'Use your biometric to authenticate',
      });

      if (!success) {
        throw new Error('Biometric authentication failed');
      }

      // Retrieve stored credentials
      const storedEmail = await SecureStore.getItemAsync('biometric_email');
      const storedPassword = await SecureStore.getItemAsync('biometric_password');

      if (!storedEmail || !storedPassword) {
        throw new Error('No stored credentials found');
      }

      return this.login({
        email: storedEmail,
        password: storedPassword,
      });
    } catch (error) {
      throw new Error(`Biometric login failed: ${error}`);
    }
  }

  async saveBiometricCredentials(email: string, password: string): Promise<void> {
    try {
      await Promise.all([
        SecureStore.setItemAsync('biometric_email', email),
        SecureStore.setItemAsync('biometric_password', password),
      ]);
    } catch (error) {
      console.warn('Failed to save biometric credentials:', error);
    }
  }

  async checkBiometricAvailability(): Promise<BiometricData> {
    try {
      const rnBiometrics = new ReactNativeBiometrics();
      const { available, biometryType } = await rnBiometrics.isSensorAvailable();

      return {
        available,
        biometryType: biometryType || 'none',
      };
    } catch (error) {
      return {
        available: false,
        biometryType: 'none',
      };
    }
  }

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout', {});
    } catch (error) {
      console.error('Logout API call failed:', error);
    } finally {
      await Promise.all([
        SecureStore.deleteItemAsync('access_token'),
        SecureStore.deleteItemAsync('refresh_token'),
        SecureStore.deleteItemAsync('user'),
        SecureStore.deleteItemAsync('biometric_email'),
        SecureStore.deleteItemAsync('biometric_password'),
      ]);
    }
  }

  async getCurrentUser() {
    const userJson = await SecureStore.getItemAsync('user');
    return userJson ? JSON.parse(userJson) : null;
  }

  async isAuthenticated(): Promise<boolean> {
    const token = await SecureStore.getItemAsync('access_token');
    return !!token;
  }
}

export default AuthService.getInstance();
