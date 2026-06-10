import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@hooks/useAppStore';
import {
  setDefects,
  addDefect,
  updateDefect,
  deleteDefect,
  setLoading,
  setError,
} from '@store/slices/defectSlice';
import { apiClient } from '@services/apiClient';

export const useDefects = () => {
  const dispatch = useAppDispatch();
  const defects = useAppSelector(state => state.defects);

  const fetchDefects = useCallback(
    async (projectId: string, filters?: any) => {
      try {
        dispatch(setLoading(true));
        const response = await apiClient.get(`/api/v1/projects/${projectId}/defects`, {
          params: filters,
        });
        dispatch(setDefects(response.data));
        dispatch(setError(null));
      } catch (error: any) {
        dispatch(setError(error.message));
        console.error('Failed to fetch defects:', error);
      } finally {
        dispatch(setLoading(false));
      }
    },
    [dispatch]
  );

  const createDefect = useCallback(
    async (projectId: string, data: any) => {
      try {
        dispatch(setLoading(true));
        const response = await apiClient.post(`/api/v1/projects/${projectId}/defects`, data);
        dispatch(addDefect(response.data));
        dispatch(setError(null));
        return response.data;
      } catch (error: any) {
        dispatch(setError(error.message));
        throw error;
      } finally {
        dispatch(setLoading(false));
      }
    },
    [dispatch]
  );

  const updateDefectData = useCallback(
    async (projectId: string, defectId: string, data: any) => {
      try {
        dispatch(setLoading(true));
        const response = await apiClient.put(
          `/api/v1/projects/${projectId}/defects/${defectId}`,
          data
        );
        dispatch(updateDefect(response.data));
        dispatch(setError(null));
        return response.data;
      } catch (error: any) {
        dispatch(setError(error.message));
        throw error;
      } finally {
        dispatch(setLoading(false));
      }
    },
    [dispatch]
  );

  const deleteDefectData = useCallback(
    async (projectId: string, defectId: string) => {
      try {
        dispatch(setLoading(true));
        await apiClient.delete(`/api/v1/projects/${projectId}/defects/${defectId}`);
        dispatch(deleteDefect(defectId));
        dispatch(setError(null));
      } catch (error: any) {
        dispatch(setError(error.message));
        throw error;
      } finally {
        dispatch(setLoading(false));
      }
    },
    [dispatch]
  );

  const addComment = useCallback(
    async (projectId: string, defectId: string, comment: string) => {
      try {
        const response = await apiClient.post(
          `/api/v1/projects/${projectId}/defects/${defectId}/comments`,
          { content: comment }
        );
        return response.data;
      } catch (error: any) {
        console.error('Failed to add comment:', error);
        throw error;
      }
    },
    []
  );

  return {
    defects: defects.items,
    loading: defects.loading,
    error: defects.error,
    fetchDefects,
    createDefect,
    updateDefectData,
    deleteDefectData,
    addComment,
  };
};
