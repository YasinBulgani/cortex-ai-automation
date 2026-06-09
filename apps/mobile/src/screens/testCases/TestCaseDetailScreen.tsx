import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation, useRoute } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { updateTestCase } from '@store/slices/testCaseSlice';
import type { RootState, AppDispatch } from '@store/index';

const TestCaseDetailScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const dispatch = useDispatch<AppDispatch>();
  const { selectedProject } = useSelector((state: RootState) => state.ui);
  const testCase = route.params?.testCase;

  const [title, setTitle] = useState(testCase?.title || '');
  const [description, setDescription] = useState(testCase?.description || '');
  const [steps, setSteps] = useState(testCase?.steps || []);
  const [stepText, setStepText] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleAddStep = () => {
    if (!stepText.trim()) return;

    const newStep = {
      id: Math.random().toString(),
      order: steps.length + 1,
      action: stepText,
      expected_result: '',
    };

    setSteps([...steps, newStep]);
    setStepText('');
  };

  const handleRemoveStep = (stepId: string) => {
    setSteps(steps.filter(s => s.id !== stepId));
  };

  const handleSave = async () => {
    if (!title.trim()) {
      Alert.alert('Error', 'Test case title is required');
      return;
    }

    if (!selectedProject || !testCase?.id) {
      Alert.alert('Error', 'Project or test case ID is missing');
      return;
    }

    setIsSaving(true);
    try {
      await dispatch(
        updateTestCase({
          projectId: selectedProject,
          testCaseId: testCase.id,
          data: {
            title,
            description,
            steps,
          },
        }),
      ).unwrap();

      Alert.alert('Success', 'Test case updated successfully');
      navigation.goBack();
    } catch (error) {
      Alert.alert('Error', error as string);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Title</Text>
        <TextInput
          style={styles.input}
          placeholder="Enter test case title"
          placeholderTextColor="#999"
          value={title}
          onChangeText={setTitle}
          editable={!isSaving}
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Description</Text>
        <TextInput
          style={[styles.input, styles.textArea]}
          placeholder="Enter test case description"
          placeholderTextColor="#999"
          value={description}
          onChangeText={setDescription}
          multiline
          numberOfLines={4}
          editable={!isSaving}
        />
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Steps</Text>
          <Text style={styles.stepCount}>{steps.length} steps</Text>
        </View>

        <View style={styles.stepInputContainer}>
          <TextInput
            style={styles.stepInput}
            placeholder="Add a test step..."
            placeholderTextColor="#999"
            value={stepText}
            onChangeText={setStepText}
            editable={!isSaving}
          />
          <TouchableOpacity
            style={styles.addStepButton}
            onPress={handleAddStep}
            disabled={!stepText.trim() || isSaving}
          >
            <Icon name="add" size={20} color="white" />
          </TouchableOpacity>
        </View>

        {steps.map((step, index) => (
          <View key={step.id} style={styles.stepItem}>
            <View style={styles.stepNumber}>
              <Text style={styles.stepNumberText}>{index + 1}</Text>
            </View>
            <View style={styles.stepContent}>
              <Text style={styles.stepAction}>{step.action}</Text>
            </View>
            <TouchableOpacity onPress={() => handleRemoveStep(step.id)}>
              <Icon name="close" size={20} color="#FF3B30" />
            </TouchableOpacity>
          </View>
        ))}
      </View>

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.button, styles.cancelButton]}
          onPress={() => navigation.goBack()}
          disabled={isSaving}
        >
          <Text style={styles.cancelButtonText}>Cancel</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.saveButton, isSaving && styles.buttonDisabled]}
          onPress={handleSave}
          disabled={isSaving}
        >
          <Text style={styles.saveButtonText}>
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  section: {
    backgroundColor: 'white',
    marginHorizontal: 12,
    marginVertical: 8,
    borderRadius: 8,
    padding: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  stepCount: {
    fontSize: 12,
    color: '#999',
    backgroundColor: '#f5f5f5',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  input: {
    backgroundColor: '#f5f5f5',
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: '#333',
    marginTop: 8,
    borderColor: '#ddd',
    borderWidth: 1,
  },
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  stepInputContainer: {
    flexDirection: 'row',
    marginBottom: 16,
  },
  stepInput: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: '#333',
    marginRight: 8,
    borderColor: '#ddd',
    borderWidth: 1,
  },
  addStepButton: {
    backgroundColor: '#007AFF',
    borderRadius: 6,
    width: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  stepItem: {
    flexDirection: 'row',
    backgroundColor: '#f9f9f9',
    borderRadius: 6,
    padding: 12,
    marginBottom: 8,
    alignItems: 'center',
  },
  stepNumber: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  stepNumberText: {
    color: 'white',
    fontWeight: '600',
    fontSize: 12,
  },
  stepContent: {
    flex: 1,
  },
  stepAction: {
    fontSize: 14,
    color: '#333',
  },
  actions: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 16,
    gap: 10,
  },
  button: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cancelButton: {
    backgroundColor: '#f5f5f5',
    borderColor: '#ddd',
    borderWidth: 1,
  },
  cancelButtonText: {
    color: '#333',
    fontSize: 14,
    fontWeight: '600',
  },
  saveButton: {
    backgroundColor: '#007AFF',
  },
  saveButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
});

export default TestCaseDetailScreen;
