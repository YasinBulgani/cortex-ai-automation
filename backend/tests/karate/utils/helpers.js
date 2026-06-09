/**
 * Karate Helper Functions
 * Common utilities for API test scenarios
 */

/**
 * Extract JWT token from login response
 */
function getToken(loginResponse) {
  if (!loginResponse || !loginResponse.access_token) {
    throw new Error('Invalid login response: no access token');
  }
  return loginResponse.access_token;
}

/**
 * Wait for async operation to complete with timeout
 */
function waitForStatus(client, path, token, expectedStatus, maxWaitMs) {
  var maxWait = maxWaitMs || 30000;
  var pollIntervalMs = 500;
  var startTime = java.lang.System.currentTimeMillis();
  var currentStatus = null;

  while (java.lang.System.currentTimeMillis() - startTime < maxWait) {
    var response = client.get(path, { headers: { 'Authorization': 'Bearer ' + token } });
    currentStatus = response.status;

    if (currentStatus === expectedStatus) {
      return response;
    }

    try {
      java.lang.Thread.sleep(pollIntervalMs);
    } catch (e) {
      // InterruptedException, continue
    }
  }

  throw new Error('Timeout waiting for status ' + expectedStatus + ', got ' + currentStatus);
}

/**
 * Generate unique test data identifier
 */
function generateUniqId(prefix) {
  var timestamp = java.lang.System.currentTimeMillis();
  var random = java.lang.Math.floor(java.lang.Math.random() * 10000);
  return (prefix || 'test') + '_' + timestamp + '_' + random;
}

/**
 * Extract error message from error response
 */
function getErrorMessage(errorResponse) {
  if (typeof errorResponse === 'string') {
    return errorResponse;
  }
  if (errorResponse.detail) {
    return errorResponse.detail;
  }
  if (errorResponse.message) {
    return errorResponse.message;
  }
  return JSON.stringify(errorResponse);
}

/**
 * Create authorization header
 */
function authHeader(token) {
  return { 'Authorization': 'Bearer ' + token };
}

/**
 * Merge headers
 */
function mergeHeaders(baseHeaders, additionalHeaders) {
  var merged = {};
  for (var key in baseHeaders) {
    merged[key] = baseHeaders[key];
  }
  for (var key in additionalHeaders) {
    merged[key] = additionalHeaders[key];
  }
  return merged;
}

/**
 * Check if response contains pagination metadata
 */
function hasPagination(response) {
  return response.total !== undefined && response.page !== undefined && response.size !== undefined;
}

/**
 * Assert response has standard error structure
 */
function assertErrorResponse(response, expectedStatus, expectedDetailPattern) {
  if (response.detail === undefined) {
    throw new Error('Response missing error detail field');
  }
  if (expectedDetailPattern && !response.detail.match(expectedDetailPattern)) {
    throw new Error('Error detail "' + response.detail + '" does not match pattern "' + expectedDetailPattern + '"');
  }
  return true;
}

// Export functions
var helpers = {
  getToken: getToken,
  waitForStatus: waitForStatus,
  generateUniqId: generateUniqId,
  getErrorMessage: getErrorMessage,
  authHeader: authHeader,
  mergeHeaders: mergeHeaders,
  hasPagination: hasPagination,
  assertErrorResponse: assertErrorResponse
};
