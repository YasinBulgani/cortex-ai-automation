import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

const PREFIX = 'neurex_';

class StorageManager {
  async setItem(key: string, value: any): Promise<void> {
    try {
      const serialized = JSON.stringify(value);
      await AsyncStorage.setItem(`${PREFIX}${key}`, serialized);
    } catch (error) {
      console.error(`Error setting item ${key}:`, error);
      throw error;
    }
  }

  async getItem<T>(key: string, defaultValue?: T): Promise<T | null> {
    try {
      const value = await AsyncStorage.getItem(`${PREFIX}${key}`);
      if (value === null) return defaultValue ?? null;
      return JSON.parse(value) as T;
    } catch (error) {
      console.error(`Error getting item ${key}:`, error);
      return defaultValue ?? null;
    }
  }

  async removeItem(key: string): Promise<void> {
    try {
      await AsyncStorage.removeItem(`${PREFIX}${key}`);
    } catch (error) {
      console.error(`Error removing item ${key}:`, error);
      throw error;
    }
  }

  async clear(): Promise<void> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const prefixedKeys = keys.filter(key => key.startsWith(PREFIX));
      await AsyncStorage.multiRemove(prefixedKeys);
    } catch (error) {
      console.error('Error clearing storage:', error);
      throw error;
    }
  }

  async setSecure(key: string, value: string): Promise<void> {
    try {
      await SecureStore.setItemAsync(`${PREFIX}${key}`, value);
    } catch (error) {
      console.error(`Error setting secure item ${key}:`, error);
      throw error;
    }
  }

  async getSecure(key: string): Promise<string | null> {
    try {
      return await SecureStore.getItemAsync(`${PREFIX}${key}`);
    } catch (error) {
      console.error(`Error getting secure item ${key}:`, error);
      return null;
    }
  }

  async removeSecure(key: string): Promise<void> {
    try {
      await SecureStore.deleteItemAsync(`${PREFIX}${key}`);
    } catch (error) {
      console.error(`Error removing secure item ${key}:`, error);
      throw error;
    }
  }
}

export default new StorageManager();
