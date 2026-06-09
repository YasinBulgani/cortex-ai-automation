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

  // Function to generate tokens for each user
  function generateTokens() {
    var tokens = {};
    var tokenResponse;

    // Generate admin token
    try {
      tokenResponse = karate.call('post', {
        url: baseUrl + '/api/v1/auth/login',
        data: {
          email: testUsers.admin.email,
          password: testUsers.admin.password
        }
      });
      tokens.admin = tokenResponse.response.access_token;
      karate.log('Admin token generated successfully');
    } catch (e) {
      karate.log('WARNING: Failed to generate admin token: ' + e.message);
      tokens.admin = 'mock-admin-token';
    }

    // Generate manager token
    try {
      tokenResponse = karate.call('post', {
        url: baseUrl + '/api/v1/auth/login',
        data: {
          email: testUsers.manager.email,
          password: testUsers.manager.password
        }
      });
      tokens.manager = tokenResponse.response.access_token;
      karate.log('Manager token generated successfully');
    } catch (e) {
      karate.log('WARNING: Failed to generate manager token: ' + e.message);
      tokens.manager = 'mock-manager-token';
    }

    // Generate tester token
    try {
      tokenResponse = karate.call('post', {
        url: baseUrl + '/api/v1/auth/login',
        data: {
          email: testUsers.tester.email,
          password: testUsers.tester.password
        }
      });
      tokens.tester = tokenResponse.response.access_token;
      karate.log('Tester token generated successfully');
    } catch (e) {
      karate.log('WARNING: Failed to generate tester token: ' + e.message);
      tokens.tester = 'mock-tester-token';
    }

    // Generate viewer token
    try {
      tokenResponse = karate.call('post', {
        url: baseUrl + '/api/v1/auth/login',
        data: {
          email: testUsers.viewer.email,
          password: testUsers.viewer.password
        }
      });
      tokens.viewer = tokenResponse.response.access_token;
      karate.log('Viewer token generated successfully');
    } catch (e) {
      karate.log('WARNING: Failed to generate viewer token: ' + e.message);
      tokens.viewer = 'mock-viewer-token';
    }

    return tokens;
  }

  // Generate all tokens at startup
  var testTokens = generateTokens();

  // Shared test data
  var testData = {
    projectName: 'Karate Test Project ' + java.lang.System.currentTimeMillis(),
    testCaseName: 'TC-Karate-' + java.lang.System.currentTimeMillis(),
    timestamp: java.lang.System.currentTimeMillis(),

    // Test user IDs (to be populated during test execution)
    adminUserId: null,
    managerUserId: null,
    testerUserId: null,
    viewerUserId: null,
    existingUserId: null,
    otherUserId: null,
    otherUserToken: null,
    otherTenantToken: null,

    // Project/Org/Team IDs
    currentOrgId: null,
    currentProjectId: null,
    currentTeamId: null,
    currentDefectId: null,
    currentCommentId: null,
    currentIntegrationId: null,
    currentWebhookId: null,
    currentTestCaseId: null,
    currentTestRunId: null,
    existingMemberId: null,

    // Other org/tenant for cross-tenant testing
    otherOrgId: null,

    // Temporary IDs for deletion tests
    tempUserId: null,
    tempProjectId: null,
    tempTeamId: null,
    tempDefectId: null,
    tempCommentId: null,
    tempIntegrationId: null,
    tempWebhookId: null,
    tempTestCaseId: null,
    tempTestRunId: null
  };

  return {
    baseUrl: baseUrl,
    env: env,
    headers: headers,
    testUsers: testUsers,
    testTokens: testTokens,
    testData: testData,
    adminToken: testTokens.admin,
    managerToken: testTokens.manager,
    testerToken: testTokens.tester,
    viewerToken: testTokens.viewer,
    currentProjectId: null,
    currentTestCaseId: null
  };
}
