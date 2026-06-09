import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import apiClient from '@services/apiClient';

interface TestCase {
  id: string;
  title: string;
  description: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  status: 'draft' | 'active' | 'archived';
  tags: string[];
  steps: Step[];
}

interface Step {
  id: string;
  order: number;
  action: string;
  expected_result: string;
}

interface TestCaseState {
  items: TestCase[];
  selectedTestCase: TestCase | null;
  isLoading: boolean;
  error: string | null;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };
}

const initialState: TestCaseState = {
  items: [],
  selectedTestCase: null,
  isLoading: false,
  error: null,
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0,
  },
};

export const fetchTestCases = createAsyncThunk(
  'testCases/fetchTestCases',
  async (
    { projectId, page = 1, pageSize = 20 }: { projectId: string; page?: number; pageSize?: number },
    { rejectWithValue },
  ) => {
    try {
      const response = await apiClient.get<{
        data: TestCase[];
        total: number;
      }>(`/projects/${projectId}/test-cases`, {
        params: { page, page_size: pageSize },
      });
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch test cases');
    }
  },
);

export const createTestCase = createAsyncThunk(
  'testCases/createTestCase',
  async (
    {
      projectId,
      data,
    }: { projectId: string; data: Omit<TestCase, 'id' | 'created_at' | 'updated_at'> },
    { rejectWithValue },
  ) => {
    try {
      const response = await apiClient.post<TestCase>(
        `/projects/${projectId}/test-cases`,
        data,
      );
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to create test case');
    }
  },
);

export const updateTestCase = createAsyncThunk(
  'testCases/updateTestCase',
  async (
    {
      projectId,
      testCaseId,
      data,
    }: {
      projectId: string;
      testCaseId: string;
      data: Partial<TestCase>;
    },
    { rejectWithValue },
  ) => {
    try {
      const response = await apiClient.put<TestCase>(
        `/projects/${projectId}/test-cases/${testCaseId}`,
        data,
      );
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to update test case');
    }
  },
);

export const deleteTestCase = createAsyncThunk(
  'testCases/deleteTestCase',
  async ({ projectId, testCaseId }: { projectId: string; testCaseId: string }, { rejectWithValue }) => {
    try {
      await apiClient.delete(`/projects/${projectId}/test-cases/${testCaseId}`);
      return testCaseId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to delete test case');
    }
  },
);

const testCaseSlice = createSlice({
  name: 'testCases',
  initialState,
  reducers: {
    selectTestCase: (state, action: PayloadAction<TestCase | null>) => {
      state.selectedTestCase = action.payload;
    },
    clearError: state => {
      state.error = null;
    },
  },
  extraReducers: builder => {
    // Fetch test cases
    builder
      .addCase(fetchTestCases.pending, state => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchTestCases.fulfilled, (state, action) => {
        state.isLoading = false;
        state.items = action.payload.data;
        state.pagination.total = action.payload.total;
      })
      .addCase(fetchTestCases.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Create test case
    builder
      .addCase(createTestCase.fulfilled, (state, action) => {
        state.items.unshift(action.payload);
        state.pagination.total += 1;
      })
      .addCase(createTestCase.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // Update test case
    builder
      .addCase(updateTestCase.fulfilled, (state, action) => {
        const index = state.items.findIndex(tc => tc.id === action.payload.id);
        if (index !== -1) {
          state.items[index] = action.payload;
        }
        if (state.selectedTestCase?.id === action.payload.id) {
          state.selectedTestCase = action.payload;
        }
      })
      .addCase(updateTestCase.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // Delete test case
    builder
      .addCase(deleteTestCase.fulfilled, (state, action) => {
        state.items = state.items.filter(tc => tc.id !== action.payload);
        state.pagination.total -= 1;
        if (state.selectedTestCase?.id === action.payload) {
          state.selectedTestCase = null;
        }
      })
      .addCase(deleteTestCase.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const { selectTestCase, clearError } = testCaseSlice.actions;
export default testCaseSlice.reducer;
