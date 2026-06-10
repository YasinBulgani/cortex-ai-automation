import { useCallback, useState } from 'react';
import { useAppDispatch, useAppSelector } from '@hooks/useAppStore';
import {
  setTestCases,
  addTestCase,
  updateTestCase,
  deleteTestCase,
  setLoading,
  setError,
} from '@store/slices/testCaseSlice';
import { apiClient } from '@services/apiClient';

export const useTestCases = () => {
  const dispatch = useAppDispatch();
  const testCases = useAppSelector(state => state.testCases);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const fetchTestCases = useCallback(
    async (projectId: string, filters?: any) => {
      try {
        dispatch(setLoading(true));
        const response = await apiClient.get(`/api/v1/projects/${projectId}/test-cases`, {
          params: filters,
        });
        dispatch(setTestCases(response.data));
        dispatch(setError(null));
      } catch (error: any) {
        dispatch(setError(error.message));
        console.error('Failed to fetch test cases:', error);
      } finally {
        dispatch(setLoading(false));
      }
    },
    [dispatch]
  );

  const createTestCase = useCallback(
    async (projectId: string, data: any) => {
      try {
        dispatch(setLoading(true));
        const response = await apiClient.post(
          `/api/v1/projects/${projectId}/test-cases`,
          data
        );
        dispatch(addTestCase(response.data));
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

  const updateTestCaseData = useCallback(
    async (projectId: string, testCaseId: string, data: any) => {
      try {
        dispatch(setLoading(true));
        const response = await apiClient.put(
          `/api/v1/projects/${projectId}/test-cases/${testCaseId}`,
          data
        );
        dispatch(updateTestCase(response.data));
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

  const deleteTestCaseData = useCallback(
    async (projectId: string, testCaseId: string) => {
      try {
        dispatch(setLoading(true));
        await apiClient.delete(
          `/api/v1/projects/${projectId}/test-cases/${testCaseId}`
        );
        dispatch(deleteTestCase(testCaseId));
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

  const selectTestCase = useCallback((id: string) => {
    setSelectedId(id);
  }, []);

  const selectedTestCase = selectedId
    ? testCases.items.find(tc => tc.id === selectedId)
    : null;

  return {
    testCases: testCases.items,
    loading: testCases.loading,
    error: testCases.error,
    selectedTestCase,
    selectedId,
    fetchTestCases,
    createTestCase,
    updateTestCaseData,
    deleteTestCaseData,
    selectTestCase,
  };
};
