import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import testCaseReducer from './slices/testCaseSlice';
import executionReducer from './slices/executionSlice';
import defectReducer from './slices/defectSlice';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    testCases: testCaseReducer,
    execution: executionReducer,
    defects: defectReducer,
    ui: uiReducer,
  },
  middleware: getDefaultMiddleware =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['auth/loginSuccess'],
        ignoredPaths: ['auth.user'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
