import React from 'react';
import { View, StyleSheet, Text, TouchableOpacity } from 'react-native';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';

interface TestCaseCardProps {
  id: string;
  title: string;
  description?: string;
  status?: 'passed' | 'failed' | 'pending' | 'skipped';
  lastRun?: string;
  onPress: () => void;
  onLongPress?: () => void;
}

const TestCaseCard: React.FC<TestCaseCardProps> = ({
  title,
  description,
  status,
  lastRun,
  onPress,
  onLongPress,
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'passed':
        return '#10b981';
      case 'failed':
        return '#ef4444';
      case 'pending':
        return '#f59e0b';
      case 'skipped':
        return '#999';
      default:
        return '#d1d5db';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'passed':
        return 'check-circle';
      case 'failed':
        return 'cancel';
      case 'pending':
        return 'schedule';
      case 'skipped':
        return 'skip-next';
      default:
        return 'help';
    }
  };

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={onPress}
      onLongPress={onLongPress}
      activeOpacity={0.7}
    >
      <View style={styles.header}>
        <Text style={styles.title} numberOfLines={2}>
          {title}
        </Text>
        {status && (
          <MaterialIcons
            name={getStatusIcon()}
            size={20}
            color={getStatusColor()}
          />
        )}
      </View>

      {description && (
        <Text style={styles.description} numberOfLines={2}>
          {description}
        </Text>
      )}

      {lastRun && (
        <View style={styles.footer}>
          <MaterialIcons name="access-time" size={14} color="#999" />
          <Text style={styles.lastRun}>{lastRun}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginVertical: 8,
    marginHorizontal: 16,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
    flex: 1,
  },
  description: {
    fontSize: 13,
    color: '#666',
    marginBottom: 8,
    lineHeight: 18,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  lastRun: {
    fontSize: 12,
    color: '#999',
  },
});

export default TestCaseCard;
