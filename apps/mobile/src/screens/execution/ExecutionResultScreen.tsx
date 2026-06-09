import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Dimensions,
} from 'react-native';
import { useRoute } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialIcons';

const { width } = Dimensions.get('window');

const ExecutionResultScreen: React.FC = () => {
  const route = useRoute<any>();
  const result = route.params?.result;

  if (!result) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>No result data available</Text>
      </View>
    );
  }

  const passRate = Math.round((1 / 1) * 100); // Placeholder

  return (
    <ScrollView style={styles.container}>
      {/* Status Summary */}
      <View style={styles.statusSection}>
        <View
          style={[
            styles.statusBadge,
            result.status === 'passed' && styles.statusPassedBg,
            result.status === 'failed' && styles.statusFailedBg,
          ]}
        >
          <Icon
            name={result.status === 'passed' ? 'check-circle' : 'error'}
            size={32}
            color="white"
          />
          <Text style={styles.statusText}>{result.status.toUpperCase()}</Text>
        </View>

        <View style={styles.stats}>
          <View style={styles.statItem}>
            <Text style={styles.statLabel}>Duration</Text>
            <Text style={styles.statValue}>{result.duration_seconds}s</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statLabel}>Completed</Text>
            <Text style={styles.statValue}>
              {new Date(result.completed_at).toLocaleDateString()}
            </Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statLabel}>Screenshots</Text>
            <Text style={styles.statValue}>{result.screenshots?.length || 0}</Text>
          </View>
        </View>
      </View>

      {/* Logs */}
      {result.logs && result.logs.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Execution Logs</Text>
          <View style={styles.logsContainer}>
            {result.logs.slice(0, 10).map((log: string, index: number) => (
              <Text key={index} style={styles.logLine}>
                {log}
              </Text>
            ))}
            {result.logs.length > 10 && (
              <Text style={styles.moreLogsText}>
                ... and {result.logs.length - 10} more logs
              </Text>
            )}
          </View>
        </View>
      )}

      {/* Screenshots */}
      {result.screenshots && result.screenshots.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Screenshots</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {result.screenshots.map((screenshot: string, index: number) => (
              <View key={index} style={styles.screenshotContainer}>
                <Image
                  source={{ uri: screenshot }}
                  style={styles.screenshot}
                  resizeMode="contain"
                />
                <Text style={styles.screenshotLabel}>Screenshot {index + 1}</Text>
              </View>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Error Message */}
      {result.error_message && (
        <View style={[styles.section, styles.errorSection]}>
          <View style={styles.errorHeader}>
            <Icon name="error-outline" size={20} color="#FF3B30" />
            <Text style={styles.errorTitle}>Error Details</Text>
          </View>
          <Text style={styles.errorMessage}>{result.error_message}</Text>
        </View>
      )}

      {/* Actions */}
      <View style={styles.actions}>
        <TouchableOpacity style={[styles.button, styles.retryButton]}>
          <Icon name="refresh" size={18} color="#007AFF" />
          <Text style={styles.retryButtonText}>Retry Execution</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[styles.button, styles.reportButton]}>
          <Icon name="file-download" size={18} color="white" />
          <Text style={styles.reportButtonText}>Download Report</Text>
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
  statusSection: {
    backgroundColor: 'white',
    paddingHorizontal: 16,
    paddingVertical: 24,
    alignItems: 'center',
  },
  statusBadge: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  statusPassedBg: {
    backgroundColor: '#34C759',
  },
  statusFailedBg: {
    backgroundColor: '#FF3B30',
  },
  statusText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
    marginTop: 8,
  },
  stats: {
    flexDirection: 'row',
    width: '100%',
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statLabel: {
    fontSize: 12,
    color: '#999',
    marginBottom: 6,
  },
  statValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  section: {
    backgroundColor: 'white',
    marginHorizontal: 12,
    marginVertical: 8,
    borderRadius: 8,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  logsContainer: {
    backgroundColor: '#1a1a1a',
    borderRadius: 6,
    padding: 12,
  },
  logLine: {
    fontSize: 12,
    color: '#00ff00',
    fontFamily: 'Courier New',
    lineHeight: 18,
  },
  moreLogsText: {
    fontSize: 12,
    color: '#666',
    marginTop: 8,
    fontStyle: 'italic',
  },
  screenshotContainer: {
    marginRight: 12,
    alignItems: 'center',
  },
  screenshot: {
    width: width - 80,
    height: 300,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
  },
  screenshotLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 8,
  },
  errorSection: {
    borderColor: '#FF3B30',
    borderWidth: 1,
    backgroundColor: '#FFF5F5',
  },
  errorHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  errorTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FF3B30',
    marginLeft: 8,
  },
  errorMessage: {
    fontSize: 13,
    color: '#666',
    lineHeight: 20,
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
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  retryButton: {
    backgroundColor: 'white',
    borderColor: '#007AFF',
    borderWidth: 1,
  },
  retryButtonText: {
    color: '#007AFF',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
  reportButton: {
    backgroundColor: '#007AFF',
  },
  reportButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
  errorText: {
    fontSize: 16,
    color: '#999',
    textAlign: 'center',
    marginTop: 20,
  },
});

export default ExecutionResultScreen;
