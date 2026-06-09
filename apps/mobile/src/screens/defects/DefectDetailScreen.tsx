import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  FlatList,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation, useRoute } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { updateDefect, addDefectComment } from '@store/slices/defectSlice';
import type { RootState, AppDispatch } from '@store/index';

const DefectDetailScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const dispatch = useDispatch<AppDispatch>();
  const { selectedProject } = useSelector((state: RootState) => state.ui);
  const defect = route.params?.defect;

  const [title, setTitle] = useState(defect?.title || '');
  const [description, setDescription] = useState(defect?.description || '');
  const [status, setStatus] = useState(defect?.status || 'new');
  const [severity, setSeverity] = useState(defect?.severity || 'medium');
  const [newComment, setNewComment] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    if (!title.trim()) {
      Alert.alert('Error', 'Defect title is required');
      return;
    }

    if (!selectedProject || !defect?.id) {
      Alert.alert('Error', 'Project or defect ID is missing');
      return;
    }

    setIsSaving(true);
    try {
      await dispatch(
        updateDefect({
          projectId: selectedProject,
          defectId: defect.id,
          data: {
            title,
            description,
            status: status as any,
            severity: severity as any,
          },
        }),
      ).unwrap();

      Alert.alert('Success', 'Defect updated successfully');
      navigation.goBack();
    } catch (error) {
      Alert.alert('Error', error as string);
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) {
      Alert.alert('Error', 'Comment cannot be empty');
      return;
    }

    if (!selectedProject || !defect?.id) return;

    try {
      await dispatch(
        addDefectComment({
          projectId: selectedProject,
          defectId: defect.id,
          comment: newComment,
        }),
      ).unwrap();

      setNewComment('');
      Alert.alert('Success', 'Comment added');
    } catch (error) {
      Alert.alert('Error', error as string);
    }
  };

  const renderComment = ({ item }: { item: any }) => (
    <View style={styles.comment}>
      <View style={styles.commentHeader}>
        <Text style={styles.commentAuthor}>User</Text>
        <Text style={styles.commentDate}>
          {new Date(item.created_at).toLocaleDateString()}
        </Text>
      </View>
      <Text style={styles.commentText}>{item.text}</Text>
    </View>
  );

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Title</Text>
        <TextInput
          style={styles.input}
          placeholder="Enter defect title"
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
          placeholder="Enter defect description"
          placeholderTextColor="#999"
          value={description}
          onChangeText={setDescription}
          multiline
          numberOfLines={4}
          editable={!isSaving}
        />
      </View>

      <View style={styles.row}>
        <View style={[styles.section, styles.halfSection]}>
          <Text style={styles.sectionTitle}>Status</Text>
          <View style={styles.segmentControl}>
            {['new', 'assigned', 'in_progress', 'resolved'].map(s => (
              <TouchableOpacity
                key={s}
                style={[
                  styles.segmentButton,
                  status === s && styles.segmentButtonActive,
                ]}
                onPress={() => setStatus(s)}
              >
                <Text
                  style={[
                    styles.segmentButtonText,
                    status === s && styles.segmentButtonTextActive,
                  ]}
                >
                  {s.replace('_', ' ')}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={[styles.section, styles.halfSection]}>
          <Text style={styles.sectionTitle}>Severity</Text>
          <View style={styles.segmentControl}>
            {['low', 'medium', 'high', 'critical'].map(s => (
              <TouchableOpacity
                key={s}
                style={[
                  styles.segmentButton,
                  severity === s && styles.segmentButtonActive,
                ]}
                onPress={() => setSeverity(s)}
              >
                <Text
                  style={[
                    styles.segmentButtonText,
                    severity === s && styles.segmentButtonTextActive,
                  ]}
                >
                  {s}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </View>

      {/* Comments Section */}
      {defect?.comments && defect.comments.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Comments ({defect.comments.length})</Text>
          <FlatList
            data={defect.comments}
            renderItem={renderComment}
            keyExtractor={item => item.id}
            scrollEnabled={false}
          />
        </View>
      )}

      {/* Add Comment */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Add Comment</Text>
        <View style={styles.commentInputContainer}>
          <TextInput
            style={styles.commentInput}
            placeholder="Write a comment..."
            placeholderTextColor="#999"
            value={newComment}
            onChangeText={setNewComment}
            multiline
            numberOfLines={3}
          />
          <TouchableOpacity
            style={[
              styles.commentButton,
              !newComment.trim() && styles.buttonDisabled,
            ]}
            onPress={handleAddComment}
            disabled={!newComment.trim()}
          >
            <Icon name="send" size={18} color="white" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Actions */}
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
  row: {
    flexDirection: 'row',
  },
  halfSection: {
    flex: 1,
    marginHorizontal: 4,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  input: {
    backgroundColor: '#f5f5f5',
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: '#333',
    borderColor: '#ddd',
    borderWidth: 1,
  },
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  segmentControl: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  segmentButton: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    marginRight: 6,
    marginBottom: 6,
    backgroundColor: '#f5f5f5',
    borderRadius: 4,
    borderColor: '#ddd',
    borderWidth: 1,
  },
  segmentButtonActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  segmentButtonText: {
    fontSize: 12,
    color: '#666',
    fontWeight: '500',
  },
  segmentButtonTextActive: {
    color: 'white',
  },
  comment: {
    backgroundColor: '#f9f9f9',
    borderRadius: 6,
    padding: 10,
    marginBottom: 8,
  },
  commentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  commentAuthor: {
    fontSize: 12,
    fontWeight: '600',
    color: '#333',
  },
  commentDate: {
    fontSize: 11,
    color: '#999',
  },
  commentText: {
    fontSize: 13,
    color: '#666',
    lineHeight: 18,
  },
  commentInputContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  commentInput: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: '#333',
    borderColor: '#ddd',
    borderWidth: 1,
    maxHeight: 100,
  },
  commentButton: {
    backgroundColor: '#007AFF',
    borderRadius: 6,
    width: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
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
});

export default DefectDetailScreen;
