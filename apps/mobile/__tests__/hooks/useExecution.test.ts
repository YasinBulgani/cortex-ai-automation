import { renderHook, act } from '@testing-library/react-native';
import { useExecution } from '@hooks/useExecution';
import { Provider } from 'react-redux';
import { store } from '@store/index';
import React from 'react';

const wrapper = ({ children }: any) => React.createElement(Provider, { store }, children);

describe('useExecution Hook', () => {
  it('should return execution state', () => {
    const { result } = renderHook(() => useExecution(), { wrapper });

    expect(result.current.execution).toBeDefined();
    expect(result.current.startTestExecution).toBeDefined();
    expect(result.current.stopTestExecution).toBeDefined();
  });

  it('should provide execution methods', () => {
    const { result } = renderHook(() => useExecution(), { wrapper });

    expect(typeof result.current.startTestExecution).toBe('function');
    expect(typeof result.current.stopTestExecution).toBe('function');
    expect(typeof result.current.pauseTestExecution).toBe('function');
    expect(typeof result.current.resumeTestExecution).toBe('function');
    expect(typeof result.current.updateExecutionProgress).toBe('function');
    expect(typeof result.current.addLog).toBe('function');
    expect(typeof result.current.finishExecution).toBe('function');
  });

  it('should update progress', () => {
    const { result } = renderHook(() => useExecution(), { wrapper });

    act(() => {
      result.current.updateExecutionProgress('exec-1', {
        passedTests: 5,
        failedTests: 0,
      });
    });

    expect(result.current.execution).toBeDefined();
  });
});
