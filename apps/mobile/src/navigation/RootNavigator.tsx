import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Icon from 'react-native-vector-icons/MaterialIcons';

import LoginScreen from '@screens/auth/LoginScreen';
import DashboardScreen from '@screens/dashboard/DashboardScreen';
import TestCasesScreen from '@screens/testCases/TestCasesScreen';
import TestCaseDetailScreen from '@screens/testCases/TestCaseDetailScreen';
import ExecutionScreen from '@screens/execution/ExecutionScreen';
import ExecutionResultScreen from '@screens/execution/ExecutionResultScreen';
import DefectsScreen from '@screens/defects/DefectsScreen';
import DefectDetailScreen from '@screens/defects/DefectDetailScreen';
import SettingsScreen from '@screens/settings/SettingsScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

interface RootNavigatorProps {
  isAuthenticated: boolean;
}

const AuthStack: React.FC = () => (
  <Stack.Navigator
    screenOptions={{
      headerShown: false,
      animationEnabled: true,
    }}
  >
    <Stack.Screen name="Login" component={LoginScreen} />
  </Stack.Navigator>
);

const TestCasesStack: React.FC = () => (
  <Stack.Navigator
    screenOptions={{
      headerBackTitleVisible: false,
    }}
  >
    <Stack.Screen
      name="TestCasesList"
      component={TestCasesScreen}
      options={{ title: 'Test Cases' }}
    />
    <Stack.Screen
      name="TestCaseDetail"
      component={TestCaseDetailScreen}
      options={{ title: 'Test Case Details' }}
    />
  </Stack.Navigator>
);

const ExecutionStack: React.FC = () => (
  <Stack.Navigator
    screenOptions={{
      headerBackTitleVisible: false,
    }}
  >
    <Stack.Screen
      name="ExecutionList"
      component={ExecutionScreen}
      options={{ title: 'Test Execution' }}
    />
    <Stack.Screen
      name="ExecutionResult"
      component={ExecutionResultScreen}
      options={{ title: 'Execution Results' }}
    />
  </Stack.Navigator>
);

const DefectsStack: React.FC = () => (
  <Stack.Navigator
    screenOptions={{
      headerBackTitleVisible: false,
    }}
  >
    <Stack.Screen
      name="DefectsList"
      component={DefectsScreen}
      options={{ title: 'Defects' }}
    />
    <Stack.Screen
      name="DefectDetail"
      component={DefectDetailScreen}
      options={{ title: 'Defect Details' }}
    />
  </Stack.Navigator>
);

const AppTabs: React.FC = () => (
  <Tab.Navigator
    screenOptions={({ route }) => ({
      tabBarIcon: ({ color, size }) => {
        let iconName = 'dashboard';

        if (route.name === 'Dashboard') iconName = 'dashboard';
        else if (route.name === 'TestCases') iconName = 'assignment';
        else if (route.name === 'Execution') iconName = 'play-arrow';
        else if (route.name === 'Defects') iconName = 'bug-report';
        else if (route.name === 'Settings') iconName = 'settings';

        return <Icon name={iconName} size={size} color={color} />;
      },
      tabBarActiveTintColor: '#007AFF',
      tabBarInactiveTintColor: '#999',
      headerShown: true,
      headerBackTitleVisible: false,
    })}
  >
    <Tab.Screen
      name="Dashboard"
      component={DashboardScreen}
      options={{ title: 'Dashboard' }}
    />
    <Tab.Screen
      name="TestCases"
      component={TestCasesStack}
      options={{ headerShown: false, title: 'Test Cases' }}
    />
    <Tab.Screen
      name="Execution"
      component={ExecutionStack}
      options={{ headerShown: false, title: 'Execution' }}
    />
    <Tab.Screen
      name="Defects"
      component={DefectsStack}
      options={{ headerShown: false, title: 'Defects' }}
    />
    <Tab.Screen
      name="Settings"
      component={SettingsScreen}
      options={{ title: 'Settings' }}
    />
  </Tab.Navigator>
);

export const RootNavigator: React.FC<RootNavigatorProps> = ({ isAuthenticated }) => {
  return isAuthenticated ? <AppTabs /> : <AuthStack />;
};
