import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Pressable,
} from 'react-native';
import { useSelector, useDispatch } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { fetchDefects } from '@store/slices/defectSlice';
import type { RootState, AppDispatch } from '@store/index';

const DefectsScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const dispatch = useDispatch<AppDispatch>();
  const { items, isLoading } = useSelector((state: RootState) => state.defects);
  const { selectedProject } = useSelector((state: RootState) => state.ui);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  useEffect(() => {
    if (selectedProject) {
      dispatch(fetchDefects({ projectId: selectedProject, status: statusFilter }));
    }
  }, [selectedProject, statusFilter, dispatch]);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '#FF3B30';
      case 'high':
        return '#FF9500';
      case 'medium':
        return '#FFA500';
      case 'low':
        return '#34C759';
      default:
        return '#999';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new':
        return '#007AFF';
      case 'assigned':
        return '#5856D6';
      case 'in_progress':
        return '#FF9500';
      case 'resolved':
        return '#34C759';
      case 'closed':
        return '#999';
      default:
        return '#ddd';
    }
  };

  const renderDefectItem = ({ item }: { item: any }) => (
    <TouchableOpacity
      style={styles.defectItem}
      onPress={() => navigation.navigate('DefectDetail', { defect: item })}
    >
      <View style={styles.defectHeader}>
        <View style={[styles.severityBadge, { backgroundColor: getSeverityColor(item.severity) }]}>
          <Text style={styles.severityText}>{item.severity[0].toUpperCase()}</Text>
        </View>

        <View style={styles.defectTitleContainer}>
          <Text style={styles.defectTitle} numberOfLines={1}>
            {item.title}
          </Text>
          <Text style={styles.defectId}>#{item.id.slice(0, 8)}</Text>
        </View>

        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) }]}>
          <Text style={styles.statusBadgeText}>{item.status.replace('_', ' ')}</Text>
        </View>
      </View>

      <Text style={styles.defectDescription} numberOfLines={2}>
        {item.description}
      </Text>

      <View style={styles.defectFooter}>
        <View style={styles.footerLeft}>
          <Icon name="calendar-today" size={14} color="#999" />
          <Text style={styles.footerText}>
            {new Date(item.created_at).toLocaleDateString()}
          </Text>
        </View>

        {item.comments && item.comments.length > 0 && (
          <View style={styles.footerRight}>
            <Icon name="mode-comment" size={14} color="#999" />
            <Text style={styles.footerText}>{item.comments.length}</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      {/* Filter Tabs */}
      <View style={styles.filterTabs}>
        {['All', 'New', 'In Progress', 'Resolved'].map(filter => (
          <Pressable
            key={filter}
            style={[
              styles.filterTab,
              (filter === 'All' && !statusFilter) ||
              (filter !== 'All' && filter.toLowerCase().replace(' ', '_') === statusFilter)
                ? styles.filterTabActive
                : null,
            ]}
            onPress={() =>
              setStatusFilter(filter === 'All' ? undefined : filter.toLowerCase().replace(' ', '_'))
            }
          >
            <Text
              style={[
                styles.filterTabText,
                (filter === 'All' && !statusFilter) ||
                (filter !== 'All' && filter.toLowerCase().replace(' ', '_') === statusFilter)
                  ? styles.filterTabTextActive
                  : null,
              ]}
            >
              {filter}
            </Text>
          </Pressable>
        ))}
      </View>

      {isLoading ? (
        <ActivityIndicator size="large" color="#007AFF" style={styles.loader} />
      ) : items.length > 0 ? (
        <FlatList
          data={items}
          renderItem={renderDefectItem}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.listContent}
          scrollEnabled={true}
        />
      ) : (
        <View style={styles.emptyContainer}>
          <Icon name="check-circle" size={48} color="#ddd" />
          <Text style={styles.emptyText}>No defects found</Text>
          <Text style={styles.emptySubtext}>Great work! All issues resolved.</Text>
        </View>
      )}

      {/* FAB */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('DefectDetail')}
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
  filterTabs: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 12,
    backgroundColor: 'white',
    borderBottomColor: '#f0f0f0',
    borderBottomWidth: 1,
  },
  filterTab: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 8,
    borderRadius: 16,
    backgroundColor: '#f5f5f5',
  },
  filterTabActive: {
    backgroundColor: '#007AFF',
  },
  filterTabText: {
    fontSize: 13,
    color: '#666',
    fontWeight: '500',
  },
  filterTabTextActive: {
    color: 'white',
  },
  loader: {
    flex: 1,
    justifyContent: 'center',
  },
  listContent: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    paddingBottom: 80,
  },
  defectItem: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    borderLeftColor: '#FF3B30',
    borderLeftWidth: 3,
  },
  defectHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  severityBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  severityText: {
    color: 'white',
    fontWeight: '600',
    fontSize: 14,
  },
  defectTitleContainer: {
    flex: 1,
  },
  defectTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  defectId: {
    fontSize: 11,
    color: '#999',
    marginTop: 2,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  statusBadgeText: {
    fontSize: 11,
    color: 'white',
    fontWeight: '500',
  },
  defectDescription: {
    fontSize: 13,
    color: '#666',
    lineHeight: 18,
    marginBottom: 10,
  },
  defectFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  footerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  footerRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  footerText: {
    fontSize: 12,
    color: '#999',
    marginLeft: 4,
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
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#FF3B30',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
  },
});

export default DefectsScreen;
