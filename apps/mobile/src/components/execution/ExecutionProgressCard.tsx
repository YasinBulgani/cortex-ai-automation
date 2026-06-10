import React from 'react';
import { View, StyleSheet, Text, Animated } from 'react-native';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';

interface ExecutionProgressCardProps {
  totalTests: number;
  passedTests: number;
  failedTests: number;
  skippedTests: number;
  duration?: string;
  status?: 'running' | 'completed' | 'failed' | 'paused';
}

const ExecutionProgressCard: React.FC<ExecutionProgressCardProps> = ({
  totalTests,
  passedTests,
  failedTests,
  skippedTests,
  duration,
  status,
}) => {
  const progressPercentage = totalTests > 0 ? (passedTests + failedTests) / totalTests : 0;

  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return '#3b82f6';
      case 'completed':
        return '#10b981';
      case 'failed':
        return '#ef4444';
      case 'paused':
        return '#f59e0b';
      default:
        return '#d1d5db';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return 'hourglass-bottom';
      case 'completed':
        return 'check-circle';
      case 'failed':
        return 'error';
      case 'paused':
        return 'pause-circle';
      default:
        return 'help';
    }
  };

  return (
    <View style={[styles.card, { borderLeftColor: getStatusColor() }]}>
      <View style={styles.header}>
        <Text style={styles.title}>Execution Progress</Text>
        <View style={styles.statusBadge}>
          <MaterialIcons
            name={getStatusIcon()}
            size={16}
            color={getStatusColor()}
          />
          <Text style={[styles.statusText, { color: getStatusColor() }]}>
            {status?.toUpperCase()}
          </Text>
        </View>
      </View>

      <View style={styles.progressContainer}>
        <View style={styles.progressBar}>
          <Animated.View
            style={[
              styles.progressFill,
              { width: `${progressPercentage * 100}%` },
            ]}
          />
        </View>
        <Text style={styles.progressText}>
          {passedTests + failedTests} of {totalTests}
        </Text>
      </View>

      <View style={styles.stats}>
        <View style={styles.statItem}>
          <MaterialIcons name="check-circle" size={16} color="#10b981" />
          <Text style={styles.statLabel}>Passed</Text>
          <Text style={styles.statValue}>{passedTests}</Text>
        </View>

        <View style={styles.statItem}>
          <MaterialIcons name="cancel" size={16} color="#ef4444" />
          <Text style={styles.statLabel}>Failed</Text>
          <Text style={styles.statValue}>{failedTests}</Text>
        </View>

        <View style={styles.statItem}>
          <MaterialIcons name="skip-next" size={16} color="#f59e0b" />
          <Text style={styles.statLabel}>Skipped</Text>
          <Text style={styles.statValue}>{skippedTests}</Text>
        </View>

        {duration && (
          <View style={styles.statItem}>
            <MaterialIcons name="schedule" size={16} color="#666" />
            <Text style={styles.statLabel}>Duration</Text>
            <Text style={styles.statValue}>{duration}</Text>
          </View>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginVertical: 8,
    marginHorizontal: 16,
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 3,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    color: '#000',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: '#f5f5f5',
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  progressContainer: {
    marginBottom: 16,
  },
  progressBar: {
    height: 8,
    backgroundColor: '#e5e7eb',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 8,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#10b981',
  },
  progressText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'right',
  },
  stats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  statItem: {
    alignItems: 'center',
    flex: 1,
  },
  statLabel: {
    fontSize: 11,
    color: '#999',
    marginTop: 4,
  },
  statValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#000',
    marginTop: 2,
  },
});

export default ExecutionProgressCard;
