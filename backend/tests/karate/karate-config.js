function() {
  var baseUrl = karate.properties['base.url'] || 'http://localhost:8000';
  var env = karate.properties['env'] || 'dev';

  karate.configure('connectTimeout', 10000);
  karate.configure('readTimeout', 30000);
  karate.configure('logPrintOptions', true);
  karate.configure('report', { showLog: true, showAllSteps: false });

  // Global headers for all requests
  var headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Accept-Language': 'en-US'
  };

  // Test users by role
  var testUsers = {
    admin: { email: 'admin@example.com', password: 'admin123' },
    manager: { email: 'manager@example.com', password: 'manager123' },
    tester: { email: 'tester@example.com', password: 'tester123' },
    viewer: { email: 'viewer@example.com', password: 'viewer123' }
  };

  // Shared test data
  var testData = {
    projectName: 'Karate Test Project ' + java.lang.System.currentTimeMillis(),
    testCaseName: 'TC-Karate-' + java.lang.System.currentTimeMillis(),
    timestamp: java.lang.System.currentTimeMillis()
  };

  return {
    baseUrl: baseUrl,
    env: env,
    headers: headers,
    testUsers: testUsers,
    testData: testData,
    adminToken: null,
    currentProjectId: null,
    currentTestCaseId: null
  };
}
