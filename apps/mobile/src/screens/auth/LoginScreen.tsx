import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
  Alert,
  Platform,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import authService from '@services/authService';
import {
  loginWithCredentials,
  loginWithOAuth,
  loginWithBiometrics,
} from '@store/slices/authSlice';
import type { RootState, AppDispatch } from '@store/index';

const LoginScreen: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { isLoading, error } = useSelector((state: RootState) => state.auth);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [biometricAvailable, setBiometricAvailable] = useState(false);

  useEffect(() => {
    checkBiometricAvailability();
  }, []);

  const checkBiometricAvailability = async () => {
    try {
      const biometrics = await authService.checkBiometricAvailability();
      setBiometricAvailable(biometrics.available);
    } catch (error) {
      setBiometricAvailable(false);
    }
  };

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please enter email and password');
      return;
    }

    try {
      const result = await dispatch(
        loginWithCredentials({ email, password }),
      ).unwrap();
      // Save credentials for biometric login if user wants to
      if (biometricAvailable) {
        Alert.alert(
          'Save Credentials',
          'Would you like to enable biometric login?',
          [
            {
              text: 'No',
              onPress: () => {},
            },
            {
              text: 'Yes',
              onPress: () => authService.saveBiometricCredentials(email, password),
            },
          ],
        );
      }
    } catch (error) {
      Alert.alert('Login Failed', error as string);
    }
  };

  const handleOAuthLogin = async () => {
    try {
      await dispatch(loginWithOAuth()).unwrap();
    } catch (error) {
      Alert.alert('OAuth Login Failed', error as string);
    }
  };

  const handleBiometricLogin = async () => {
    try {
      await dispatch(loginWithBiometrics()).unwrap();
    } catch (error) {
      Alert.alert('Biometric Login Failed', error as string);
    }
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
    >
      <View style={styles.header}>
        <Icon name="security" size={64} color="#007AFF" />
        <Text style={styles.title}>Neurex</Text>
        <Text style={styles.subtitle}>Test Automation Platform</Text>
      </View>

      <View style={styles.form}>
        <View style={styles.inputGroup}>
          <Text style={styles.label}>Email</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter your email"
            placeholderTextColor="#999"
            value={email}
            onChangeText={setEmail}
            editable={!isLoading}
            autoCapitalize="none"
            keyboardType="email-address"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Password</Text>
          <View style={styles.passwordContainer}>
            <TextInput
              style={styles.passwordInput}
              placeholder="Enter your password"
              placeholderTextColor="#999"
              value={password}
              onChangeText={setPassword}
              editable={!isLoading}
              secureTextEntry={!showPassword}
            />
            <TouchableOpacity
              onPress={() => setShowPassword(!showPassword)}
              disabled={isLoading}
            >
              <Icon
                name={showPassword ? 'visibility-off' : 'visibility'}
                size={24}
                color="#007AFF"
              />
            </TouchableOpacity>
          </View>
        </View>

        {error && <Text style={styles.errorText}>{error}</Text>}

        <TouchableOpacity
          style={[styles.button, styles.primaryButton, isLoading && styles.buttonDisabled]}
          onPress={handleLogin}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text style={styles.buttonText}>Sign In</Text>
          )}
        </TouchableOpacity>

        <View style={styles.divider}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>Or</Text>
          <View style={styles.dividerLine} />
        </View>

        <TouchableOpacity
          style={[styles.button, styles.outlineButton, isLoading && styles.buttonDisabled]}
          onPress={handleOAuthLogin}
          disabled={isLoading}
        >
          <Icon name="account-circle" size={20} color="#007AFF" />
          <Text style={styles.outlineButtonText}>Sign in with OAuth</Text>
        </TouchableOpacity>

        {biometricAvailable && (
          <TouchableOpacity
            style={[styles.button, styles.outlineButton, isLoading && styles.buttonDisabled]}
            onPress={handleBiometricLogin}
            disabled={isLoading}
          >
            <Icon name="fingerprint" size={20} color="#007AFF" />
            <Text style={styles.outlineButtonText}>Biometric Login</Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Don't have an account? <Text style={styles.footerLink}>Sign Up</Text>
        </Text>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  contentContainer: {
    flexGrow: 1,
    justifyContent: 'space-between',
    padding: 20,
  },
  header: {
    alignItems: 'center',
    marginTop: 40,
    marginBottom: 60,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 20,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
  },
  form: {
    width: '100%',
  },
  inputGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    borderColor: '#ddd',
    borderWidth: 1,
    color: '#333',
  },
  passwordContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    borderRadius: 8,
    borderColor: '#ddd',
    borderWidth: 1,
    paddingRight: 12,
  },
  passwordInput: {
    flex: 1,
    padding: 12,
    fontSize: 16,
    color: '#333',
  },
  errorText: {
    color: '#FF3B30',
    fontSize: 14,
    marginBottom: 12,
  },
  button: {
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  primaryButton: {
    backgroundColor: '#007AFF',
  },
  outlineButton: {
    backgroundColor: 'white',
    borderColor: '#007AFF',
    borderWidth: 1,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  outlineButtonText: {
    color: '#007AFF',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 20,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#ddd',
  },
  dividerText: {
    color: '#999',
    marginHorizontal: 10,
  },
  footer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  footerText: {
    color: '#666',
    fontSize: 14,
  },
  footerLink: {
    color: '#007AFF',
    fontWeight: '600',
  },
});

export default LoginScreen;
