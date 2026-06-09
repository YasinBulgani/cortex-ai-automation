import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import apiClient from '@services/apiClient';

interface Defect {
  id: string;
  title: string;
  description: string;
  project_id: string;
  test_case_id?: string;
  status: 'new' | 'assigned' | 'in_progress' | 'resolved' | 'closed';
  severity: 'critical' | 'high' | 'medium' | 'low';
  assignee_id?: string;
  created_at: string;
  updated_at: string;
  comments: DefectComment[];
}

interface DefectComment {
  id: string;
  author_id: string;
  text: string;
  created_at: string;
}

interface DefectState {
  items: Defect[];
  selectedDefect: Defect | null;
  isLoading: boolean;
  error: string | null;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };
}

const initialState: DefectState = {
  items: [],
  selectedDefect: null,
  isLoading: false,
  error: null,
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0,
  },
};

export const fetchDefects = createAsyncThunk(
  'defects/fetchDefects',
  async (
    { projectId, page = 1, pageSize = 20, status }: { projectId: string; page?: number; pageSize?: number; status?: string },
    { rejectWithValue },
  ) => {
    try {
      const response = await apiClient.get<{
        data: Defect[];
        total: number;
      }>(`/projects/${projectId}/defects`, {
        params: { page, page_size: pageSize, status },
      });
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch defects');
    }
  },
);

export const createDefect = createAsyncThunk(
  'defects/createDefect',
  async (
    {
      projectId,
      data,
    }: {
      projectId: string;
      data: Omit<Defect, 'id' | 'created_at' | 'updated_at' | 'comments'>;
    },
    { rejectWithValue },
  ) => {
    try {
      const response = await apiClient.post<Defect>(
        `/projects/${projectId}/defects`,
        data,
      );
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to create defect');
    }
  },
);

export const updateDefect = createAsyncThunk(
  'defects/updateDefect',
  async (
    {
      projectId,
      defectId,
      data,
    }: {
      projectId: string;
      defectId: string;
      data: Partial<Defect>;
    },
    { rejectWithValue },
  ) => {
    try {
      const response = await apiClient.put<Defect>(
        `/projects/${projectId}/defects/${defectId}`,
        data,
      );
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to update defect');
    }
  },
);

export const addDefectComment = createAsyncThunk(
  'defects/addDefectComment',
  async (
    {
      projectId,
      defectId,
      comment,
    }: { projectId: string; defectId: string; comment: string },
    { rejectWithValue },
  ) => {
    try {
      const response = await apiClient.post<Defect>(
        `/projects/${projectId}/defects/${defectId}/comments`,
        { text: comment },
      );
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to add comment');
    }
  },
);

const defectSlice = createSlice({
  name: 'defects',
  initialState,
  reducers: {
    selectDefect: (state, action: PayloadAction<Defect | null>) => {
      state.selectedDefect = action.payload;
    },
    clearError: state => {
      state.error = null;
    },
  },
  extraReducers: builder => {
    // Fetch defects
    builder
      .addCase(fetchDefects.pending, state => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchDefects.fulfilled, (state, action) => {
        state.isLoading = false;
        state.items = action.payload.data;
        state.pagination.total = action.payload.total;
      })
      .addCase(fetchDefects.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Create defect
    builder
      .addCase(createDefect.fulfilled, (state, action) => {
        state.items.unshift(action.payload);
        state.pagination.total += 1;
      })
      .addCase(createDefect.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // Update defect
    builder
      .addCase(updateDefect.fulfilled, (state, action) => {
        const index = state.items.findIndex(d => d.id === action.payload.id);
        if (index !== -1) {
          state.items[index] = action.payload;
        }
        if (state.selectedDefect?.id === action.payload.id) {
          state.selectedDefect = action.payload;
        }
      })
      .addCase(updateDefect.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // Add comment
    builder
      .addCase(addDefectComment.fulfilled, (state, action) => {
        if (state.selectedDefect?.id === action.payload.id) {
          state.selectedDefect = action.payload;
        }
        const index = state.items.findIndex(d => d.id === action.payload.id);
        if (index !== -1) {
          state.items[index] = action.payload;
        }
      });
  },
});

export const { selectDefect, clearError } = defectSlice.actions;
export default defectSlice.reducer;
