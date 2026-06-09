module.exports = {
  root: true,
  extends: [
    '@react-native-community',
    'prettier'
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true
    }
  },
  plugins: [
    '@typescript-eslint',
    'prettier'
  ],
  rules: {
    'prettier/prettier': 'error',
    '@typescript-eslint/explicit-function-return-types': 'warn',
    '@typescript-eslint/no-explicit-any': 'warn',
    'react-native/no-color-literals': 'off',
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'no-unused-vars': 'off',
    '@typescript-eslint/no-unused-vars': [
      'error',
      { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }
    ]
  },
  settings: {
    react: {
      version: 'detect'
    }
  }
};
