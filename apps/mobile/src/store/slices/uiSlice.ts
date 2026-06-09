import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UIState {
  theme: 'light' | 'dark';
  notifications: Notification[];
  offlineMode: boolean;
  selectedProject: string | null;
}

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

const initialState: UIState = {
  theme: 'light',
  notifications: [],
  offlineMode: false,
  selectedProject: null,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setTheme: (state, action: PayloadAction<'light' | 'dark'>) => {
      state.theme = action.payload;
    },
    addNotification: (state, action: PayloadAction<Notification>) => {
      state.notifications.push(action.payload);
      if (action.payload.duration) {
        setTimeout(() => {
          state.notifications = state.notifications.filter(n => n.id !== action.payload.id);
        }, action.payload.duration);
      }
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload);
    },
    clearNotifications: state => {
      state.notifications = [];
    },
    setOfflineMode: (state, action: PayloadAction<boolean>) => {
      state.offlineMode = action.payload;
    },
    setSelectedProject: (state, action: PayloadAction<string | null>) => {
      state.selectedProject = action.payload;
    },
  },
});

export const {
  setTheme,
  addNotification,
  removeNotification,
  clearNotifications,
  setOfflineMode,
  setSelectedProject,
} = uiSlice.actions;

export default uiSlice.reducer;
