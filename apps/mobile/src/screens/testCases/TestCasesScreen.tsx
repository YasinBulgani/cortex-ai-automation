import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  TextInput,
  Alert,
} from 'react-native';
import { useSelector, useDispatch } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import type { RootState, AppDispatch } from '@store/index';
import { fetchTestCases, selectTestCase, deleteTestCase } from '@store/slices/testCaseSlice';

interface TestCasesScreenProps {
  navigation: any;
}

const TestCasesScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const dispatch = useDispatch<AppDispatch>();
  const { items, isLoading } = useSelector((state: RootState) => state.testCases);
  const { selectedProject } = useSelector((state: RootState) => state.ui);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredItems, setFilteredItems] = useState(items);

  useEffect(() => {
    if (selectedProject) {
      dispatch(fetchTestCases({ projectId: selectedProject }));
    }
  }, [selectedProject, dispatch]);

  useEffect(() => {
    const filtered = items.filter(tc =>
      tc.title.toLowerCase().includes(searchQuery.toLowerCase()),
    );
    setFilteredItems(filtered);
  }, [searchQuery, items]);

  const handleSelectTestCase = (testCase: any) => {
    dispatch(selectTestCase(testCase));
    navigation.navigate('TestCaseDetail', { testCase });
  };

  const handleDeleteTestCase = (testCaseId: string) => {
    Alert.alert(
      'Delete Test Case',
      'Are you sure you want to delete this test case?',
      [
        {
          text: 'Cancel',
          style: 'cancel',
        },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            if (selectedProject) {
              await dispatch(deleteTestCase({ projectId: selectedProject, testCaseId }));
            }
          },
        },
      ],
    );
  };

  const renderTestCaseItem = ({ item }: { item: any }) => (
    <TouchableOpacity
      style={styles.testCaseItem}
      onPress={() => handleSelectTestCase(item)}
    >
      <View style={styles.testCaseContent}>
        <Text style={styles.testCaseTitle} numberOfLines={1}>
          {item.title}
        </Text>
        <Text style={styles.testCaseDescription} numberOfLines={2}>
          {item.description}
        </Text>
        <View style={styles.tagsContainer}>
          {item.tags?.slice(0, 2).map((tag: string, index: number) => (
            <View key={index} style={styles.tag}>
              <Text style={styles.tagText}>{tag}</Text>
            </View>
          ))}
          {item.tags?.length > 2 && (
            <Text style={styles.moreTagsText}>+{item.tags.length - 2}</Text>
          )}
        </View>
      </View>

      <View style={styles.testCaseActions}>
        <TouchableOpacity onPress={() => handleDeleteTestCase(item.id)}>
          <Icon name="delete" size={20} color="#FF3B30" />
        </TouchableOpacity>
        <Icon name="chevron-right" size={24} color="#999" style={styles.chevron} />
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.searchContainer}>
        <Icon name="search" size={20} color="#999" />
        <TextInput
          style={styles.searchInput}
          placeholder="Search test cases..."
          placeholderTextColor="#999"
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
      </View>

      {isLoading ? (
        <ActivityIndicator size="large" color="#007AFF" style={styles.loader} />
      ) : filteredItems.length > 0 ? (
        <FlatList
          data={filteredItems}
          renderItem={renderTestCaseItem}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.listContent}
          scrollEnabled={true}
        />
      ) : (
        <View style={styles.emptyContainer}>
          <Icon name="assignment" size={48} color="#ddd" />
          <Text style={styles.emptyText}>No test cases found</Text>
          <TouchableOpacity style={styles.createButton}>
            <Icon name="add" size={20} color="#fff" />
            <Text style={styles.createButtonText}>Create Test Case</Text>
          </TouchableOpacity>
        </View>
      )}

      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('TestCaseDetail')}
      >
        <Icon name="add" size={24} color="white" />
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    marginHorizontal: 12,
    marginVertical: 12,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderColor: '#ddd',
    borderWidth: 1,
  },
  searchInput: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 8,
    fontSize: 14,
    color: '#333',
  },
  loader: {
    flex: 1,
    justifyContent: 'center',
  },
  listContent: {
    paddingHorizontal: 12,
    paddingBottom: 80,
  },
  testCaseItem: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    alignItems: 'center',
  },
  testCaseContent: {
    flex: 1,
  },
  testCaseTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  testCaseDescription: {
    fontSize: 13,
    color: '#999',
    marginTop: 4,
  },
  tagsContainer: {
    flexDirection: 'row',
    marginTop: 8,
  },
  tag: {
    backgroundColor: '#F2F2F7',
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginRight: 6,
  },
  tagText: {
    fontSize: 11,
    color: '#666',
  },
  moreTagsText: {
    fontSize: 11,
    color: '#999',
    marginLeft: 4,
  },
  testCaseActions: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 8,
  },
  chevron: {
    marginLeft: 8,
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
  createButton: {
    flexDirection: 'row',
    backgroundColor: '#007AFF',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    marginTop: 20,
    alignItems: 'center',
  },
  createButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
  },
});

export default TestCasesScreen;
