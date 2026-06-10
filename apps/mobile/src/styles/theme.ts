export const colors = {
  // Primary
  primary: '#3b82f6',
  primaryLight: '#dbeafe',
  primaryDark: '#1e40af',

  // Secondary
  secondary: '#8b5cf6',
  secondaryLight: '#ede9fe',
  secondaryDark: '#5b21b6',

  // Semantic
  success: '#10b981',
  successLight: '#d1fae5',
  successDark: '#065f46',

  error: '#ef4444',
  errorLight: '#fee2e2',
  errorDark: '#7f1d1d',

  warning: '#f59e0b',
  warningLight: '#fef3c7',
  warningDark: '#92400e',

  info: '#06b6d4',
  infoLight: '#cffafe',
  infoDark: '#164e63',

  // Neutral
  black: '#000000',
  white: '#ffffff',
  gray50: '#f9fafb',
  gray100: '#f3f4f6',
  gray200: '#e5e7eb',
  gray300: '#d1d5db',
  gray400: '#9ca3af',
  gray500: '#6b7280',
  gray600: '#4b5563',
  gray700: '#374151',
  gray800: '#1f2937',
  gray900: '#111827',

  // Special
  transparent: 'transparent',
  overlay: 'rgba(0, 0, 0, 0.5)',
};

export const typography = {
  h1: {
    fontSize: 32,
    fontWeight: '700',
    lineHeight: 40,
  },
  h2: {
    fontSize: 28,
    fontWeight: '700',
    lineHeight: 36,
  },
  h3: {
    fontSize: 24,
    fontWeight: '700',
    lineHeight: 32,
  },
  h4: {
    fontSize: 20,
    fontWeight: '700',
    lineHeight: 28,
  },
  h5: {
    fontSize: 18,
    fontWeight: '600',
    lineHeight: 24,
  },
  h6: {
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 20,
  },
  body: {
    fontSize: 14,
    fontWeight: '400',
    lineHeight: 20,
  },
  bodySmall: {
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 18,
  },
  caption: {
    fontSize: 11,
    fontWeight: '400',
    lineHeight: 16,
  },
  button: {
    fontSize: 14,
    fontWeight: '600',
    lineHeight: 20,
  },
};

export const spacing = {
  0: 0,
  2: 2,
  4: 4,
  6: 6,
  8: 8,
  12: 12,
  16: 16,
  20: 20,
  24: 24,
  32: 32,
  40: 40,
  48: 48,
};

export const borderRadius = {
  none: 0,
  xs: 2,
  sm: 4,
  md: 6,
  lg: 8,
  xl: 12,
  '2xl': 16,
  full: 9999,
};

export const shadows = {
  none: {
    shadowColor: 'transparent',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 2,
    elevation: 1,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 3,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 5,
  },
  xl: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.2,
    shadowRadius: 15,
    elevation: 10,
  },
};

export const lightTheme = {
  colors: {
    ...colors,
    background: colors.white,
    surface: colors.gray50,
    text: colors.gray900,
    textSecondary: colors.gray600,
    border: colors.gray200,
  },
  typography,
  spacing,
  borderRadius,
  shadows,
};

export const darkTheme = {
  colors: {
    ...colors,
    background: colors.gray900,
    surface: colors.gray800,
    text: colors.white,
    textSecondary: colors.gray400,
    border: colors.gray700,
  },
  typography,
  spacing,
  borderRadius,
  shadows,
};

export type Theme = typeof lightTheme;
export default lightTheme;
