import authService from '@services/authService';
import * as SecureStore from 'expo-secure-store';

jest.mock('expo-secure-store');

describe('AuthService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('isAuthenticated', () => {
    it('should return true when access token exists', async () => {
      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('test-token');

      const result = await authService.isAuthenticated();

      expect(result).toBe(true);
      expect(SecureStore.getItemAsync).toHaveBeenCalledWith('access_token');
    });

    it('should return false when access token does not exist', async () => {
      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(null);

      const result = await authService.isAuthenticated();

      expect(result).toBe(false);
    });
  });

  describe('getCurrentUser', () => {
    it('should return user object when stored', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        name: 'Test User',
      };

      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(JSON.stringify(mockUser));

      const result = await authService.getCurrentUser();

      expect(result).toEqual(mockUser);
    });

    it('should return null when no user is stored', async () => {
      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(null);

      const result = await authService.getCurrentUser();

      expect(result).toBeNull();
    });
  });

  describe('logout', () => {
    it('should clear all auth-related data', async () => {
      await authService.logout();

      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('access_token');
      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('refresh_token');
      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('user');
    });
  });

  describe('checkBiometricAvailability', () => {
    it('should check biometric availability', async () => {
      const result = await authService.checkBiometricAvailability();

      expect(result).toHaveProperty('available');
      expect(result).toHaveProperty('biometryType');
    });
  });
});
