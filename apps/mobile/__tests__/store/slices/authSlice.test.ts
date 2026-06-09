import authReducer, { clearError } from '@store/slices/authSlice';

describe('authSlice', () => {
  const initialState = {
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
  };

  it('should return the initial state', () => {
    expect(authReducer(undefined, { type: 'unknown' })).toEqual(initialState);
  });

  describe('clearError', () => {
    it('should clear error messages', () => {
      const previousState = {
        ...initialState,
        error: 'Test error',
      };

      const result = authReducer(previousState, clearError());

      expect(result.error).toBeNull();
    });
  });

  it('should handle login pending state', () => {
    const action = {
      type: 'auth/loginWithCredentials/pending',
    };

    const result = authReducer(initialState, action);

    expect(result.isLoading).toBe(true);
    expect(result.error).toBeNull();
  });

  it('should handle login fulfilled state', () => {
    const payload = {
      access_token: 'test-token',
      user: {
        id: '123',
        email: 'test@example.com',
        name: 'Test User',
        org_id: 'org-123',
      },
    };

    const action = {
      type: 'auth/loginWithCredentials/fulfilled',
      payload,
    };

    const result = authReducer(initialState, action);

    expect(result.isLoading).toBe(false);
    expect(result.isAuthenticated).toBe(true);
    expect(result.token).toBe('test-token');
    expect(result.user).toEqual(payload.user);
  });

  it('should handle login rejected state', () => {
    const payload = 'Login failed';

    const action = {
      type: 'auth/loginWithCredentials/rejected',
      payload,
    };

    const result = authReducer(initialState, action);

    expect(result.isLoading).toBe(false);
    expect(result.error).toBe('Login failed');
  });
});
