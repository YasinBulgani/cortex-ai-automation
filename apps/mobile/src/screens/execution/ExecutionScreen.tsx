import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Modal,
  Alert,
} from 'react-native';
import { useSelector, useDispatch } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { startExecution, fetchExecutionResults } from '@store/slices/executionSlice';
import type { RootState, AppDispatch } from '@store/index';

const ExecutionScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const dispatch = useDispatch<AppDispatch>();
  const { results, isLoading, isRunning } = useSelector((state: RootState) => state.execution);
  const { selectedProject } = useSelector((state: RootState) => state.ui);
  const { items: testCases } = useSelector((state: RootState) => state.testCases);
  const [selectedTestCases, setSelectedTestCases] = useState<string[]>([]);
  const [showSelector, setShowSelector] = useState(false);

  useEffect(() => {
    if (selectedProject) {
      dispatch(fetchExecutionResults({ projectId: selectedProject }));
    }
  }, [selectedProject, dispatch]);

  const handleStartExecution = async () => {
    if (selectedTestCases.length === 0) {
      Alert.alert('Error', 'Please select at least one test case');
      return;
    }

    if (!selectedProject) return;

    try {
      await dispatch(
        startExecution({
          projectId: selectedProject,
          testCaseIds: selectedTestCases,
        }),
      ).unwrap();

      setSelectedTestCases([]);
      setShowSelector(false);
      Alert.alert('Success', 'Test execution started');
    } catch (error) {
      Alert.alert('Error', error as string);
    }
  };

  const handleSelectTestCase = (testCaseId: string) => {
    if (selectedTestCases.includes(testCaseId)) {
      setSelectedTestCases(selectedTestCases.filter(id => id !== testCaseId));
    } else {
      setSelectedTestCases([...selectedTestCases, testCaseId]);
    }
  };

  const renderExecutionResult = ({ item }: { item: any }) => (
    <TouchableOpacity
      style={styles.resultItem}
      onPress={() => navigation.navigate('ExecutionResult', { result: item })}
    >
      <View
        style={[
          styles.statusIndicator,
          item.status === 'passed' && styles.statusPassed,
          item.status === 'failed' && styles.statusFailed,
          item.status === 'running' && styles.statusRunning,
        ]}
      />

      <View style={styles.resultContent}>
        <Text style={styles.resultTitle}>Test Execution</Text>
        <Text style={styles.resultTime}>
          {new Date(item.started_at).toLocaleString()}
        </Text>
        <View style={styles.resultStats}>
          <Text style={styles.resultStat}>{item.duration_seconds}s</Text>
          <Text style={styles.resultStatus}>{item.status.toUpperCase()}</Text>
        </View>
      </View>

      <Icon name="chevron-right" size={24} color="#999" />
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          style={[styles.startButton, isRunning && styles.buttonDisabled]}
          onPress={() => setShowSelector(true)}
          disabled={isRunning}
        >
          <Icon name="play-arrow" size={20} color="white" />
          <Text style={styles.startButtonText}>
            {isRunning ? 'Running...' : 'Start Execution'}
          </Text>
        </TouchableOpacity>
      </View>

      {isLoading ? (
        <ActivityIndicator size="large" color="#007AFF" style={styles.loader} />
      ) : results.length > 0 ? (
        <FlatList
          data={results}
          renderItem={renderExecutionResult}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.listContent}
          scrollEnabled={true}
        />
      ) : (
        <View style={styles.emptyContainer}>
          <Icon name="assignment-late" size={48} color="#ddd" />
          <Text style={styles.emptyText}>No execution results</Text>
          <Text style={styles.emptySubtext}>
            Run test cases to see results here
          </Text>
        </View>
      )}

      {/* Test Case Selector Modal */}
      <Modal
        visible={showSelector}
        animationType="slide"
        transparent
        onRequestClose={() => setShowSelector(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modal}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select Test Cases</Text>
              <TouchableOpacity onPress={() => setShowSelector(false)}>
                <Icon name="close" size={24} color="#333" />
              </TouchableOpacity>
            </View>

            <FlatList
              data={testCases}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={styles.testCaseSelector}
                  onPress={() => handleSelectTestCase(item.id)}
                >
                  <View
                    style={[
                      styles.checkbox,
                      selectedTestCases.includes(item.id) && styles.checkboxChecked,
                    ]}
                  >
                    {selectedTestCases.includes(item.id) && (
                      <Icon name="check" size={16} color="white" />
                    )}
                  </View>
                  <View style={styles.testCaseInfo}>
                    <Text style={styles.testCaseTitle}>{item.title}</Text>
                    <Text style={styles.testCaseDesc} numberOfLines={1}>
                      {item.description}
                    </Text>
                  </View>
                </TouchableOpacity>
              )}
              keyExtractor={item => item.id}
              style={styles.testCasesList}
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => setShowSelector(false)}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.modalExecuteButton,
                  selectedTestCases.length === 0 && styles.buttonDisabled,
                ]}
                onPress={handleStartExecution}
                disabled={selectedTestCases.length === 0}
              >
                <Text style={styles.modalExecuteText}>
                  Run {selectedTestCases.length > 0 ? `(${selectedTestCases.length})` : ''}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    paddingHorizontal: 12,
    paddingVertical: 12,
    backgroundColor: 'white',
    borderBottomColor: '#f0f0f0',
    borderBottomWidth: 1,
  },
  startButton: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    flexDirection: 'row',
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  startButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  loader: {
    flex: 1,
    justifyContent: 'center',
  },
  listContent: {
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  resultItem: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    alignItems: 'center',
  },
  statusIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 12,
    backgroundColor: '#999',
  },
  statusPassed: {
    backgroundColor: '#34C759',
  },
  statusFailed: {
    backgroundColor: '#FF3B30',
  },
  statusRunning: {
    backgroundColor: '#FFA500',
  },
  resultContent: {
    flex: 1,
  },
  resultTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  resultTime: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  resultStats: {
    flexDirection: 'row',
    marginTop: 8,
  },
  resultStat: {
    fontSize: 12,
    color: '#007AFF',
    marginRight: 12,
  },
  resultStatus: {
    fontSize: 12,
    color: '#666',
    fontWeight: '600',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    marginTop: 12,
  },
  emptySubtext: {
    fontSize: 13,
    color: '#bbb',
    marginTop: 4,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modal: {
    backgroundColor: 'white',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    maxHeight: '85%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 16,
    borderBottomColor: '#f0f0f0',
    borderBottomWidth: 1,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  testCasesList: {
    flex: 1,
  },
  testCaseSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomColor: '#f5f5f5',
    borderBottomWidth: 1,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 4,
    borderColor: '#ddd',
    borderWidth: 1,
    marginRight: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxChecked: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  testCaseInfo: {
    flex: 1,
  },
  testCaseTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  testCaseDesc: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  modalActions: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderTopColor: '#f0f0f0',
    borderTopWidth: 1,
    gap: 10,
  },
  modalCancelButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderColor: '#ddd',
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalCancelText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  modalExecuteButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalExecuteText: {
    fontSize: 14,
    fontWeight: '600',
    color: 'white',
  },
});

export default ExecutionScreen;
