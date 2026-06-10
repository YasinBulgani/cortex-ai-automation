import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@hooks/useAppStore';
import {
  startExecution,
  stopExecution,
  pauseExecution,
  resumeExecution,
  updateProgress,
  addExecutionLog,
  setExecutionResult,
} from '@store/slices/executionSlice';
import { apiClient } from '@services/apiClient';

export const useExecution = () => {
  const dispatch = useAppDispatch();
  const execution = useAppSelector(state => state.execution);

  const startTestExecution = useCallback(
    async (testCaseId: string) => {
      try {
        dispatch(startExecution(testCaseId));
        const response = await apiClient.post(`/api/v1/test-executions/start`, {
          testCaseId,
        });
        return response.data;
      } catch (error) {
        console.error('Failed to start execution:', error);
        throw error;
      }
    },
    [dispatch]
  );

  const stopTestExecution = useCallback(
    async (executionId: string) => {
      try {
        dispatch(stopExecution(executionId));
        await apiClient.post(`/api/v1/test-executions/${executionId}/stop`);
      } catch (error) {
        console.error('Failed to stop execution:', error);
        throw error;
      }
    },
    [dispatch]
  );

  const pauseTestExecution = useCallback(
    async (executionId: string) => {
      try {
        dispatch(pauseExecution(executionId));
        await apiClient.post(`/api/v1/test-executions/${executionId}/pause`);
      } catch (error) {
        console.error('Failed to pause execution:', error);
        throw error;
      }
    },
    [dispatch]
  );

  const resumeTestExecution = useCallback(
    async (executionId: string) => {
      try {
        dispatch(resumeExecution(executionId));
        await apiClient.post(`/api/v1/test-executions/${executionId}/resume`);
      } catch (error) {
        console.error('Failed to resume execution:', error);
        throw error;
      }
    },
    [dispatch]
  );

  const updateExecutionProgress = useCallback(
    (executionId: string, progress: any) => {
      dispatch(updateProgress({ executionId, progress }));
    },
    [dispatch]
  );

  const addLog = useCallback(
    (executionId: string, log: string) => {
      dispatch(addExecutionLog({ executionId, log }));
    },
    [dispatch]
  );

  const finishExecution = useCallback(
    (executionId: string, result: any) => {
      dispatch(setExecutionResult({ executionId, result }));
    },
    [dispatch]
  );

  return {
    execution,
    startTestExecution,
    stopTestExecution,
    pauseTestExecution,
    resumeTestExecution,
    updateExecutionProgress,
    addLog,
    finishExecution,
  };
};
