import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import authService from '@services/authService';

interface User {
  id: string;
  email: string;
  name: string;
  org_id: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
};

export const loginWithCredentials = createAsyncThunk(
  'auth/loginWithCredentials',
  async ({ email, password }: { email: string; password: string }, { rejectWithValue }) => {
    try {
      const response = await authService.login({ email, password });
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Login failed');
    }
  },
);

export const loginWithOAuth = createAsyncThunk(
  'auth/loginWithOAuth',
  async (_, { rejectWithValue }) => {
    try {
      const response = await authService.loginWithOAuth();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.message || 'OAuth login failed');
    }
  },
);

export const loginWithBiometrics = createAsyncThunk(
  'auth/loginWithBiometrics',
  async (_, { rejectWithValue }) => {
    try {
      const response = await authService.loginWithBiometrics();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Biometric login failed');
    }
  },
);

export const logout = createAsyncThunk(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      await authService.logout();
      return null;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Logout failed');
    }
  },
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: state => {
      state.error = null;
    },
  },
  extraReducers: builder => {
    // Login with credentials
    builder
      .addCase(loginWithCredentials.pending, state => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginWithCredentials.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.token = action.payload.access_token;
      })
      .addCase(loginWithCredentials.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // OAuth login
    builder
      .addCase(loginWithOAuth.pending, state => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginWithOAuth.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.token = action.payload.access_token;
      })
      .addCase(loginWithOAuth.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Biometric login
    builder
      .addCase(loginWithBiometrics.pending, state => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginWithBiometrics.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.token = action.payload.access_token;
      })
      .addCase(loginWithBiometrics.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Logout
    builder
      .addCase(logout.fulfilled, state => {
        state.user = null;
        state.token = null;
        state.isAuthenticated = false;
      });
  },
});

export const { clearError } = authSlice.actions;
export default authSlice.reducer;
