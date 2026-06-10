import React from 'react';
import { View, StyleSheet, Text } from 'react-native';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';

interface EmptyProps {
  icon?: string;
  title: string;
  message?: string;
}

const Empty: React.FC<EmptyProps> = ({
  icon = 'inbox',
  title,
  message,
}) => {
  return (
    <View style={styles.container}>
      <MaterialIcons name={icon} size={48} color="#d1d5db" />
      <Text style={styles.title}>{title}</Text>
      {message && <Text style={styles.message}>{message}</Text>}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
    marginTop: 16,
    textAlign: 'center',
  },
  message: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
    textAlign: 'center',
  },
});

export default Empty;
