import React, { useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { useSelector, useDispatch } from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { RootState, AppDispatch } from '@store/index';
import { fetchExecutionResults } from '@store/slices/executionSlice';

const { width } = Dimensions.get('window');

const DashboardScreen: React.FC = () => {
  const insets = useSafeAreaInsets();
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);
  const { results, isLoading } = useSelector((state: RootState) => state.execution);
  const { items: testCases } = useSelector((state: RootState) => state.testCases);
  const { selectedProject } = useSelector((state: RootState) => state.ui);

  useEffect(() => {
    if (selectedProject) {
      dispatch(fetchExecutionResults({ projectId: selectedProject }));
    }
  }, [selectedProject, dispatch]);

  const getStats = () => {
    const stats = {
      totalTests: testCases.length,
      totalExecutions: results.length,
      passedExecutions: results.filter(r => r.status === 'passed').length,
      failedExecutions: results.filter(r => r.status === 'failed').length,
      avgDuration: results.length > 0
        ? Math.round(
            results.reduce((sum, r) => sum + (r.duration_seconds || 0), 0) / results.length,
          )
        : 0,
    };

    return stats;
  };

  const stats = getStats();
  const passRate = stats.totalExecutions > 0
    ? Math.round((stats.passedExecutions / stats.totalExecutions) * 100)
    : 0;

  return (
    <ScrollView style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Welcome back,</Text>
          <Text style={styles.userName}>{user?.name || 'User'}</Text>
        </View>
        <Icon name="notifications" size={28} color="#333" />
      </View>

      {/* Quick Stats */}
      <View style={styles.statsGrid}>
        <View style={[styles.statCard, styles.statCardPrimary]}>
          <Icon name="assignment" size={32} color="#fff" />
          <Text style={styles.statValue}>{stats.totalTests}</Text>
          <Text style={styles.statLabel}>Test Cases</Text>
        </View>

        <View style={[styles.statCard, styles.statCardSecondary]}>
          <Icon name="trending-up" size={32} color="#fff" />
          <Text style={styles.statValue}>{passRate}%</Text>
          <Text style={styles.statLabel}>Pass Rate</Text>
        </View>
      </View>

      <View style={styles.statsGrid}>
        <View style={[styles.statCard, styles.statCardSuccess]}>
          <Icon name="check-circle" size={32} color="#fff" />
          <Text style={styles.statValue}>{stats.passedExecutions}</Text>
          <Text style={styles.statLabel}>Passed</Text>
        </View>

        <View style={[styles.statCard, styles.statCardError]}>
          <Icon name="error" size={32} color="#fff" />
          <Text style={styles.statValue}>{stats.failedExecutions}</Text>
          <Text style={styles.statLabel}>Failed</Text>
        </View>
      </View>

      {/* Recent Activity */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Recent Activity</Text>

        {isLoading ? (
          <ActivityIndicator size="large" color="#007AFF" style={styles.loader} />
        ) : results.length > 0 ? (
          <View>
            {results.slice(0, 5).map(result => (
              <View key={result.id} style={styles.activityItem}>
                <View style={styles.activityIcon}>
                  <Icon
                    name={
                      result.status === 'passed'
                        ? 'check-circle'
                        : result.status === 'failed'
                          ? 'error'
                          : 'schedule'
                    }
                    size={24}
                    color={
                      result.status === 'passed'
                        ? '#34C759'
                        : result.status === 'failed'
                          ? '#FF3B30'
                          : '#FFA500'
                    }
                  />
                </View>

                <View style={styles.activityDetails}>
                  <Text style={styles.activityTitle}>Execution completed</Text>
                  <Text style={styles.activityTime}>
                    {result.duration_seconds}s • {new Date(result.completed_at).toLocaleDateString()}
                  </Text>
                </View>

                <View
                  style={[
                    styles.statusBadge,
                    result.status === 'passed' && styles.statusPassed,
                    result.status === 'failed' && styles.statusFailed,
                  ]}
                >
                  <Text
                    style={[
                      styles.statusText,
                      result.status === 'passed' && styles.statusPassedText,
                      result.status === 'failed' && styles.statusFailedText,
                    ]}
                  >
                    {result.status.toUpperCase()}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        ) : (
          <Text style={styles.emptyText}>No recent activity</Text>
        )}
      </View>

      {/* Quick Actions */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>

        <TouchableOpacity style={styles.actionButton}>
          <Icon name="add" size={28} color="#fff" />
          <Text style={styles.actionButtonText}>Create Test Case</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[styles.actionButton, styles.actionButtonSecondary]}>
          <Icon name="play-arrow" size={28} color="#007AFF" />
          <Text style={styles.actionButtonTextSecondary}>Run Tests</Text>
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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 20,
  },
  greeting: {
    fontSize: 14,
    color: '#999',
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 4,
  },
  statsGrid: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  statCard: {
    flex: 1,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginHorizontal: 5,
    minHeight: 140,
  },
  statCardPrimary: {
    backgroundColor: '#007AFF',
  },
  statCardSecondary: {
    backgroundColor: '#5856D6',
  },
  statCardSuccess: {
    backgroundColor: '#34C759',
  },
  statCardError: {
    backgroundColor: '#FF3B30',
  },
  statValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 12,
  },
  statLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 8,
  },
  section: {
    paddingHorizontal: 20,
    paddingVertical: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 16,
  },
  loader: {
    marginVertical: 20,
  },
  activityItem: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    alignItems: 'center',
  },
  activityIcon: {
    marginRight: 12,
  },
  activityDetails: {
    flex: 1,
  },
  activityTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  activityTime: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    backgroundColor: '#f5f5f5',
  },
  statusPassed: {
    backgroundColor: '#E8F5E9',
  },
  statusFailed: {
    backgroundColor: '#FFEBEE',
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#999',
  },
  statusPassedText: {
    color: '#34C759',
  },
  statusFailedText: {
    color: '#FF3B30',
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    marginVertical: 20,
  },
  actionButton: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    paddingVertical: 14,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  actionButtonSecondary: {
    backgroundColor: 'white',
    borderColor: '#007AFF',
    borderWidth: 1,
  },
  actionButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  actionButtonTextSecondary: {
    color: '#007AFF',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
});

export default DashboardScreen;
