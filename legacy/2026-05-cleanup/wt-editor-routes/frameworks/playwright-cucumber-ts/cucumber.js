require('dotenv').config();
require('ts-node').register({
  project: './tsconfig.json',
  transpileOnly: true
});

module.exports = {
  default: {
    require: [
      'steps/**/*.ts',
      'steps/**/*.js'
    ],
    format: [
      'progress-bar',
      'json:reports/cucumber-report.json',
      'html:reports/cucumber-report.html',
      '@cucumber/pretty-formatter'
    ],
    formatOptions: {
      snippetInterface: 'async-await'
    },
    paths: ['features/**/*.feature'],
    strict: true,
    tags: process.env.TAGS || '',
    parallel: process.env.PARALLEL_WORKERS ? parseInt(process.env.PARALLEL_WORKERS, 10) : 0
  }
};
