import React, { useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';

const SplashScreen: React.FC = () => {
  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Icon name="security" size={80} color="#007AFF" />
        <Text style={styles.title}>Neurex</Text>
        <Text style={styles.subtitle}>Initializing...</Text>
      </View>
      <ActivityIndicator size="large" color="#007AFF" style={styles.loader} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    alignItems: 'center',
    marginBottom: 40,
  },
  title: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 20,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
  },
  loader: {
    position: 'absolute',
    bottom: 50,
  },
});

export default SplashScreen;
