import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import { useSelector, useDispatch } from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { logout } from '@store/slices/authSlice';
import { setTheme, setOfflineMode } from '@store/slices/uiSlice';
import type { RootState, AppDispatch } from '@store/index';

const SettingsScreen: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);
  const { theme, offlineMode } = useSelector((state: RootState) => state.ui);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure you want to logout?', [
      {
        text: 'Cancel',
        style: 'cancel',
      },
      {
        text: 'Logout',
        style: 'destructive',
        onPress: async () => {
          setIsLoggingOut(true);
          try {
            await dispatch(logout()).unwrap();
          } catch (error) {
            Alert.alert('Error', 'Logout failed');
          } finally {
            setIsLoggingOut(false);
          }
        },
      },
    ]);
  };

  return (
    <ScrollView style={styles.container}>
      {/* User Profile Section */}
      <View style={styles.profileSection}>
        <View style={styles.avatar}>
          <Icon name="account-circle" size={48} color="#007AFF" />
        </View>
        <View style={styles.userInfo}>
          <Text style={styles.userName}>{user?.name || 'User'}</Text>
          <Text style={styles.userEmail}>{user?.email}</Text>
        </View>
      </View>

      {/* Appearance Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Appearance</Text>

        <View style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="brightness-4" size={24} color="#007AFF" />
            <View style={styles.settingTextContainer}>
              <Text style={styles.settingName}>Dark Mode</Text>
              <Text style={styles.settingDescription}>
                {theme === 'dark' ? 'Enabled' : 'Disabled'}
              </Text>
            </View>
          </View>
          <Switch
            value={theme === 'dark'}
            onValueChange={value => dispatch(setTheme(value ? 'dark' : 'light'))}
          />
        </View>
      </View>

      {/* Data & Storage Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Data & Storage</Text>

        <View style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="cloud-off" size={24} color="#FF9500" />
            <View style={styles.settingTextContainer}>
              <Text style={styles.settingName}>Offline Mode</Text>
              <Text style={styles.settingDescription}>
                Cache data for offline access
              </Text>
            </View>
          </View>
          <Switch
            value={offlineMode}
            onValueChange={value => dispatch(setOfflineMode(value))}
          />
        </View>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="storage" size={24} color="#5856D6" />
            <View style={styles.settingTextContainer}>
              <Text style={styles.settingName}>Clear Cache</Text>
              <Text style={styles.settingDescription}>
                Remove cached data
              </Text>
            </View>
          </View>
          <Icon name="chevron-right" size={24} color="#999" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="delete" size={24} color="#FF3B30" />
            <View style={styles.settingTextContainer}>
              <Text style={styles.settingName}>Clear All Data</Text>
              <Text style={styles.settingDescription}>
                Remove all offline data
              </Text>
            </View>
          </View>
          <Icon name="chevron-right" size={24} color="#999" />
        </TouchableOpacity>
      </View>

      {/* Security Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Security</Text>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="lock" size={24} color="#34C759" />
            <View style={styles.settingTextContainer}>
              <Text style={styles.settingName}>Change Password</Text>
              <Text style={styles.settingDescription}>
                Update your password
              </Text>
            </View>
          </View>
          <Icon name="chevron-right" size={24} color="#999" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="fingerprint" size={24} color="#007AFF" />
            <View style={styles.settingTextContainer}>
              <Text style={styles.settingName}>Biometric Authentication</Text>
              <Text style={styles.settingDescription}>
                Use fingerprint or face ID
              </Text>
            </View>
          </View>
          <Switch value={true} disabled />
        </TouchableOpacity>
      </View>

      {/* About Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>

        <View style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="info" size={24} color="#999" />
            <View style={styles.settingTextContainer}>
              <Text style={styles.settingName}>App Version</Text>
              <Text style={styles.settingDescription}>0.1.0</Text>
            </View>
          </View>
        </View>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="language" size={24} color="#5856D6" />
            <View style={styles.settingTextContainer}>
              <Text style={styles.settingName}>Language</Text>
              <Text style={styles.settingDescription}>English</Text>
            </View>
          </View>
          <Icon name="chevron-right" size={24} color="#999" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="help" size={24} color="#FF9500" />
            <View style={styles.settingTextContainer}>
              <Text style={styles.settingName}>Help & Support</Text>
              <Text style={styles.settingDescription}>
                Get help and support
              </Text>
            </View>
          </View>
          <Icon name="chevron-right" size={24} color="#999" />
        </TouchableOpacity>
      </View>

      {/* Logout Section */}
      <View style={styles.logoutSection}>
        <TouchableOpacity
          style={styles.logoutButton}
          onPress={handleLogout}
          disabled={isLoggingOut}
        >
          <Icon name="logout" size={20} color="white" />
          <Text style={styles.logoutButtonText}>
            {isLoggingOut ? 'Logging out...' : 'Logout'}
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
  profileSection: {
    backgroundColor: 'white',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 20,
    marginBottom: 8,
  },
  avatar: {
    marginRight: 16,
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  userEmail: {
    fontSize: 13,
    color: '#999',
    marginTop: 4,
  },
  section: {
    backgroundColor: 'white',
    marginVertical: 8,
    paddingVertical: 4,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomColor: '#f5f5f5',
    borderBottomWidth: 1,
  },
  settingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  settingTextContainer: {
    marginLeft: 16,
    flex: 1,
  },
  settingName: {
    fontSize: 15,
    fontWeight: '500',
    color: '#333',
  },
  settingDescription: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  logoutSection: {
    paddingHorizontal: 12,
    paddingVertical: 20,
  },
  logoutButton: {
    backgroundColor: '#FF3B30',
    borderRadius: 8,
    flexDirection: 'row',
    paddingVertical: 14,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoutButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
});

export default SettingsScreen;
