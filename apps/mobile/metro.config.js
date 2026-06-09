const { getDefaultConfig } = require('metro-config');
const path = require('path');

const projectRoot = __dirname;
const monorepoRoot = path.resolve(projectRoot, '../..');

const config = getDefaultConfig(projectRoot);

config.projectRoot = projectRoot;
config.watchFolders = [monorepoRoot];

config.resolver = {
  ...config.resolver,
  nodeModulesPaths: [
    path.resolve(projectRoot, 'node_modules'),
    path.resolve(monorepoRoot, 'node_modules'),
  ],
  extraNodeModules: {
    '@neurex/shared': path.resolve(monorepoRoot, 'packages/shared'),
    '@neurex/ui': path.resolve(monorepoRoot, 'packages/ui'),
  },
  assetExts: [
    ...config.resolver.assetExts,
    'db',
  ],
};

config.transformer = {
  ...config.transformer,
  babelTransformerPath: require.resolve('react-native-svg-transformer'),
};

config.resolver.assetExts = config.resolver.assetExts.filter(ext => ext !== 'svg');
config.resolver.sourceExts = [
  ...config.resolver.sourceExts,
  'svg',
];

module.exports = config;
