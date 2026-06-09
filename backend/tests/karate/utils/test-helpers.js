/**
 * Karate Test Helpers
 * Provides utility functions for test setup, teardown, and assertions
 */

function generateAuthToken(email) {
  // In a real scenario, this would call an actual /auth/login endpoint
  // For now, return a mock JWT-like token
  var payload = {
    sub: email,
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 3600
  };

  // In integration tests, you'd call the real auth endpoint:
  // karate.call('get', { url: baseUrl + '/api/v1/auth/login', data: {...} })
  return 'mock-jwt-token-for-' + email;
}

function setupTestData() {
  // Setup common test data structures
  return {
    timestamp: java.lang.System.currentTimeMillis(),

    // Test users
    users: {
      admin: {
        email: 'admin@example.com',
        password: 'admin123',
        firstName: 'Admin',
        lastName: 'User'
      },
      manager: {
        email: 'manager@example.com',
        password: 'manager123',
        firstName: 'Manager',
        lastName: 'User'
      },
      tester: {
        email: 'tester@example.com',
        password: 'tester123',
        firstName: 'Tester',
        lastName: 'User'
      },
      viewer: {
        email: 'viewer@example.com',
        password: 'viewer123',
        firstName: 'Viewer',
        lastName: 'User'
      }
    },

    // Test data IDs (populated during test execution)
    currentOrgId: null,
    currentProjectId: null,
    currentTeamId: null,
    currentUserId: null,
    currentDefectId: null,
    currentIntegrationId: null,
    currentWebhookId: null,
    existingUserId: null,
    existingMemberId: null,

    // Temporary IDs for deletion tests
    tempUserId: null,
    tempProjectId: null,
    tempTeamId: null,
    tempDefectId: null,
    tempIntegrationId: null,
    tempWebhookId: null,
    tempCommentId: null
  };
}

function teardownTestData(testData) {
  // Cleanup function to remove temporary test data
  karate.log('Cleaning up test data...');

  // Delete temporary resources
  var resources = [
    { path: '/api/v1/projects/' + testData.tempProjectId, method: 'delete' },
    { path: '/api/v1/users/' + testData.tempUserId, method: 'delete' },
    { path: '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.tempTeamId, method: 'delete' },
    { path: '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.tempDefectId, method: 'delete' },
    { path: '/api/v1/projects/' + testData.currentProjectId + '/webhooks/' + testData.tempWebhookId, method: 'delete' }
  ];

  resources.forEach(function(resource) {
    if (resource.path) {
      try {
        karate.call('delete', { url: resource.path });
      } catch (e) {
        karate.log('Cleanup failed for: ' + resource.path + ' - ' + e.message);
      }
    }
  });
}

function assertTenantIsolation(response, expectedTenantId) {
  // Validate that response data belongs to expected tenant
  if (!response || !expectedTenantId) {
    return true; // Skip check if not applicable
  }

  if (response.tenant_id && response.tenant_id !== expectedTenantId) {
    throw new Error('Tenant isolation violation: expected ' + expectedTenantId +
                   ' but got ' + response.tenant_id);
  }

  // Check nested resources
  if (response.items && Array.isArray(response.items)) {
    response.items.forEach(function(item) {
      if (item.tenant_id && item.tenant_id !== expectedTenantId) {
        throw new Error('Tenant isolation violation in items: expected ' + expectedTenantId +
                       ' but got ' + item.tenant_id);
      }
    });
  }

  return true;
}

function validatePaginationResponse(response) {
  // Validate pagination structure
  if (!response.total_count || typeof response.total_count !== 'number') {
    throw new Error('Missing or invalid total_count');
  }

  if (!Array.isArray(response.items)) {
    throw new Error('Missing or invalid items array');
  }

  if (typeof response.limit !== 'number' || response.limit < 1) {
    throw new Error('Missing or invalid limit');
  }

  if (typeof response.offset !== 'number' || response.offset < 0) {
    throw new Error('Missing or invalid offset');
  }

  if (response.items.length > response.limit) {
    throw new Error('Items count exceeds limit');
  }

  return true;
}

function validateErrorResponse(response, expectedStatus, expectedMessage) {
  // Validate error response structure
  if (!response.detail) {
    throw new Error('Missing error detail in response');
  }

  if (expectedMessage && !response.detail.includes(expectedMessage)) {
    throw new Error('Expected error message containing "' + expectedMessage +
                   '" but got "' + response.detail + '"');
  }

  return true;
}

function validateUUID(value) {
  // Validate UUID format (simplified)
  var uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!uuidPattern.test(value)) {
    throw new Error('Invalid UUID format: ' + value);
  }
  return true;
}

function validateEmail(email) {
  // Validate email format
  var emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(email)) {
    throw new Error('Invalid email format: ' + email);
  }
  return true;
}

function validateURL(url) {
  // Validate URL format
  try {
    new java.net.URL(url);
    return true;
  } catch (e) {
    throw new Error('Invalid URL format: ' + url);
  }
}

function waitForAsyncCompletion(path, expectedStatus, maxWaitMs) {
  // Poll an endpoint until it reaches expected status
  var maxWait = maxWaitMs || 30000;
  var pollInterval = 500;
  var elapsed = 0;

  while (elapsed < maxWait) {
    try {
      var response = karate.call('get', { url: path });
      if (response.responseCode === expectedStatus) {
        return response;
      }
    } catch (e) {
      karate.log('Poll attempt failed: ' + e.message);
    }

    java.lang.Thread.sleep(pollInterval);
    elapsed += pollInterval;
  }

  throw new Error('Timeout waiting for ' + path + ' to reach status ' + expectedStatus);
}

function createTestUser(baseUrl, adminToken, userData) {
  // Helper to create a test user
  var response = karate.call('post', {
    url: baseUrl + '/api/v1/users',
    headers: { 'Authorization': 'Bearer ' + adminToken },
    data: {
      email: userData.email,
      first_name: userData.firstName || 'Test',
      last_name: userData.lastName || 'User',
      roles: userData.roles || ['viewer']
    }
  });

  if (response.responseCode !== 201) {
    throw new Error('Failed to create test user: ' + response.responseCode);
  }

  return response.response.id;
}

function createTestProject(baseUrl, adminToken, orgId, projectData) {
  // Helper to create a test project
  var response = karate.call('post', {
    url: baseUrl + '/api/v1/projects',
    headers: { 'Authorization': 'Bearer ' + adminToken },
    data: {
      name: projectData.name,
      description: projectData.description || '',
      org_id: orgId,
      team_id: projectData.teamId
    }
  });

  if (response.responseCode !== 201) {
    throw new Error('Failed to create test project: ' + response.responseCode);
  }

  return response.response.id;
}

function createTestTeam(baseUrl, adminToken, orgId, teamData) {
  // Helper to create a test team
  var response = karate.call('post', {
    url: baseUrl + '/api/v1/organizations/' + orgId + '/teams',
    headers: { 'Authorization': 'Bearer ' + adminToken },
    data: {
      name: teamData.name,
      description: teamData.description || ''
    }
  });

  if (response.responseCode !== 201) {
    throw new Error('Failed to create test team: ' + response.responseCode);
  }

  return response.response.id;
}

function createTestOrganization(baseUrl, adminToken, orgData) {
  // Helper to create a test organization
  var response = karate.call('post', {
    url: baseUrl + '/api/v1/organizations',
    headers: { 'Authorization': 'Bearer ' + adminToken },
    data: {
      name: orgData.name,
      workspace: orgData.workspace,
      billing_email: orgData.billingEmail
    }
  });

  if (response.responseCode !== 201) {
    throw new Error('Failed to create test organization: ' + response.responseCode);
  }

  return response.response.id;
}

// Export all helpers
var helpers = {
  generateAuthToken: generateAuthToken,
  setupTestData: setupTestData,
  teardownTestData: teardownTestData,
  assertTenantIsolation: assertTenantIsolation,
  validatePaginationResponse: validatePaginationResponse,
  validateErrorResponse: validateErrorResponse,
  validateUUID: validateUUID,
  validateEmail: validateEmail,
  validateURL: validateURL,
  waitForAsyncCompletion: waitForAsyncCompletion,
  createTestUser: createTestUser,
  createTestProject: createTestProject,
  createTestTeam: createTestTeam,
  createTestOrganization: createTestOrganization
};

helpers;
