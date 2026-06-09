import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import apiClient from '@services/apiClient';

interface ExecutionResult {
  id: string;
  test_case_id: string;
  status: 'pending' | 'running' | 'passed' | 'failed' | 'skipped';
  duration_seconds: number;
  started_at: string;
  completed_at: string;
  error_message?: string;
  screenshots: string[];
  logs: string[];
}

interface ExecutionState {
  results: ExecutionResult[];
  activeExecution: ExecutionResult | null;
  isRunning: boolean;
  isLoading: boolean;
  error: string | null;
  wsConnected: boolean;
}

const initialState: ExecutionState = {
  results: [],
  activeExecution: null,
  isRunning: false,
  isLoading: false,
  error: null,
  wsConnected: false,
};

export const startExecution = createAsyncThunk(
  'execution/startExecution',
  async (
    { projectId, testCaseIds }: { projectId: string; testCaseIds: string[] },
    { rejectWithValue },
  ) => {
    try {
      const response = await apiClient.post<ExecutionResult>(
        `/projects/${projectId}/executions/start`,
        { test_case_ids: testCaseIds },
      );
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to start execution');
    }
  },
);

export const fetchExecutionResults = createAsyncThunk(
  'execution/fetchExecutionResults',
  async (
    { projectId, limit = 50 }: { projectId: string; limit?: number },
    { rejectWithValue },
  ) => {
    try {
      const response = await apiClient.get<ExecutionResult[]>(
        `/projects/${projectId}/executions`,
        { params: { limit } },
      );
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch execution results');
    }
  },
);

export const stopExecution = createAsyncThunk(
  'execution/stopExecution',
  async ({ projectId, executionId }: { projectId: string; executionId: string }, { rejectWithValue }) => {
    try {
      await apiClient.post(`/projects/${projectId}/executions/${executionId}/stop`, {});
      return executionId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to stop execution');
    }
  },
);

const executionSlice = createSlice({
  name: 'execution',
  initialState,
  reducers: {
    updateExecutionStatus: (state, action: PayloadAction<{ id: string; status: ExecutionResult['status']; duration_seconds?: number }>) => {
      const result = state.results.find(r => r.id === action.payload.id);
      if (result) {
        result.status = action.payload.status;
        if (action.payload.duration_seconds !== undefined) {
          result.duration_seconds = action.payload.duration_seconds;
        }
      }
      if (state.activeExecution?.id === action.payload.id) {
        state.activeExecution.status = action.payload.status;
      }
    },
    addExecutionLog: (state, action: PayloadAction<{ id: string; log: string }>) => {
      const result = state.results.find(r => r.id === action.payload.id);
      if (result) {
        result.logs.push(action.payload.log);
      }
    },
    addScreenshot: (state, action: PayloadAction<{ id: string; screenshot: string }>) => {
      const result = state.results.find(r => r.id === action.payload.id);
      if (result) {
        result.screenshots.push(action.payload.screenshot);
      }
    },
    setWsConnected: (state, action: PayloadAction<boolean>) => {
      state.wsConnected = action.payload;
    },
    clearError: state => {
      state.error = null;
    },
  },
  extraReducers: builder => {
    // Start execution
    builder
      .addCase(startExecution.pending, state => {
        state.isLoading = true;
        state.isRunning = true;
        state.error = null;
      })
      .addCase(startExecution.fulfilled, (state, action) => {
        state.isLoading = false;
        state.activeExecution = action.payload;
        state.results.unshift(action.payload);
      })
      .addCase(startExecution.rejected, (state, action) => {
        state.isLoading = false;
        state.isRunning = false;
        state.error = action.payload as string;
      });

    // Fetch execution results
    builder
      .addCase(fetchExecutionResults.pending, state => {
        state.isLoading = true;
      })
      .addCase(fetchExecutionResults.fulfilled, (state, action) => {
        state.isLoading = false;
        state.results = action.payload;
      })
      .addCase(fetchExecutionResults.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Stop execution
    builder
      .addCase(stopExecution.fulfilled, (state, action) => {
        state.isRunning = false;
        if (state.activeExecution?.id === action.payload) {
          state.activeExecution.status = 'skipped';
        }
      });
  },
});

export const { updateExecutionStatus, addExecutionLog, addScreenshot, setWsConnected, clearError } =
  executionSlice.actions;
export default executionSlice.reducer;
