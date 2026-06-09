module.exports = {
  presets: [
    'module:metro-react-native-babel-preset',
    ['@babel/preset-typescript', { allowNamespaces: true }],
  ],
  plugins: [
    'react-native-reanimated/plugin',
    [
      'module-resolver',
      {
        alias: {
          '@components': './src/components',
          '@screens': './src/screens',
          '@navigation': './src/navigation',
          '@services': './src/services',
          '@store': './src/store',
          '@utils': './src/utils',
          '@types': './src/types',
          '@constants': './src/constants',
          '@hooks': './src/hooks',
          '@assets': './assets',
        },
      },
    ],
  ],
};
