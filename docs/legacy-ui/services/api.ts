/**
 * API Client Service
 * Handles all HTTP requests to the backend API
 */

export interface APIClientConfig {
  baseUrl: string;
  timeout?: number;
  retryAttempts?: number;
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  steps: string[];
}

export interface TestData {
  [key: string]: string | number | boolean | null | TestData | TestData[];
}

export interface TestResults {
  runId: string;
  totalTests: number;
  passedTests: number;
  failedTests: number;
  duration: number;
}

export interface Report {
  id: string;
  title: string;
  date: string;
  content: string;
  format: 'html' | 'pdf' | 'json';
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  environment: string;
}

/**
 * API Client for backend communication
 */
export class APIClient {
  private baseUrl: string;
  private timeout: number;
  private retryAttempts: number;
  private headers: Record<string, string>;

  constructor(config: APIClientConfig) {
    this.baseUrl = config.baseUrl;
    this.timeout = config.timeout || 30000;
    this.retryAttempts = config.retryAttempts || 3;
    this.headers = {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Generic request method with retry logic
   */
  private async request<T>(
    method: string,
    endpoint: string,
    data?: Record<string, unknown>,
    attempt: number = 1
  ): Promise<T> {
    try {
      const url = `${this.baseUrl}${endpoint}`;
      const options: RequestInit = {
        method,
        headers: this.headers,
      };

      if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        options.body = JSON.stringify(data);
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const responseData = await response.json();
      return responseData as T;
    } catch (error) {
      if (attempt < this.retryAttempts) {
        console.warn(
          `Request failed (attempt ${attempt}/${this.retryAttempts}), retrying...`,
          error
        );
        await this.delay(Math.pow(2, attempt) * 1000); // Exponential backoff
        return this.request<T>(method, endpoint, data, attempt + 1);
      }

      throw error;
    }
  }

  /**
   * Delay helper for retry logic
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Set authorization token
   */
  setAuthToken(token: string): void {
    this.headers['Authorization'] = `Bearer ${token}`;
  }

  /**
   * Clear authorization token
   */
  clearAuthToken(): void {
    delete this.headers['Authorization'];
  }

  // ============================================================================
  // AI API Endpoints
  // ============================================================================

  /**
   * Generate test scenarios from user story
   */
  async generateScenarios(
    userStory: string,
    pageUrl: string,
    pageElements: string[]
  ): Promise<{ scenarios: Scenario[] }> {
    return this.request('POST', '/api/ai/generate-scenarios', {
      user_story: userStory,
      page_url: pageUrl,
      page_elements: pageElements,
    });
  }

  /**
   * Suggest test data based on scenario
   */
  async suggestTestData(
    scenarioDescription: string,
    requiredFields: string[],
    testType: string
  ): Promise<{ test_data: TestData }> {
    return this.request('POST', '/api/ai/suggest-data', {
      scenario_description: scenarioDescription,
      required_fields: requiredFields,
      test_type: testType,
    });
  }

  /**
   * Analyze test coverage
   */
  async analyzeCoverage(tests: any[], feature: string): Promise<any> {
    return this.request('POST', '/api/ai/analyze-coverage', {
      tests,
      feature,
    });
  }

  /**
   * Debug test execution
   */
  async debugTest(testName: string, error: string): Promise<any> {
    return this.request('POST', '/api/ai/debug-test', {
      test_name: testName,
      error,
    });
  }

  /**
   * Get AI statistics
   */
  async getAIStatistics(): Promise<any> {
    return this.request('GET', '/api/ai/statistics');
  }

  /**
   * Get AI configuration
   */
  async getAIConfiguration(): Promise<any> {
    return this.request('GET', '/api/ai/config');
  }

  // ============================================================================
  // Reporting API Endpoints
  // ============================================================================

  /**
   * Generate test report
   */
  async generateReport(
    runId: string,
    formats: string[]
  ): Promise<{ report: Report }> {
    return this.request('POST', '/api/reporting/generate-report', {
      run_id: runId,
      formats,
    });
  }

  /**
   * Record test run
   */
  async recordTestRun(results: TestResults): Promise<any> {
    return this.request('POST', '/api/reporting/record-run', results);
  }

  /**
   * Record test failure
   */
  async recordFailure(testName: string, error: string, stackTrace: string): Promise<any> {
    return this.request('POST', '/api/reporting/record-failure', {
      test_name: testName,
      error,
      stack_trace: stackTrace,
    });
  }

  /**
   * Get test trends
   */
  async getTrends(hours: number = 24): Promise<any> {
    return this.request('GET', `/api/reporting/analytics/trends?hours=${hours}`);
  }

  /**
   * Get risk assessment
   */
  async getRiskAssessment(): Promise<any> {
    return this.request('GET', '/api/reporting/analytics/risk-assessment');
  }

  /**
   * Get failure predictions
   */
  async getPredictions(days: number = 7): Promise<any> {
    return this.request('GET', `/api/reporting/analytics/predictions?days=${days}`);
  }

  /**
   * Get performance metrics
   */
  async getPerformanceMetrics(): Promise<any> {
    return this.request('GET', '/api/reporting/analytics/performance');
  }

  /**
   * Get comprehensive analytics report
   */
  async getAnalyticsReport(hours: number = 24): Promise<any> {
    return this.request('GET', `/api/reporting/analytics/report?hours=${hours}`);
  }

  // ============================================================================
  // Visual AI Endpoints
  // ============================================================================

  /**
   * Analyze image for visual regression
   */
  async analyzeImage(
    baselineImage: string,
    currentImage: string,
    testName: string
  ): Promise<any> {
    return this.request('POST', '/api/visual-ai/analyze', {
      baseline_image: baselineImage,
      current_image: currentImage,
      test_name: testName,
    });
  }

  /**
   * Update baseline image
   */
  async updateBaseline(testName: string, image: string): Promise<any> {
    return this.request('POST', '/api/visual-ai/update-baseline', {
      test_name: testName,
      image,
    });
  }

  /**
   * Get baseline status
   */
  async getBaselineStatus(testName: string): Promise<any> {
    return this.request('GET', `/api/visual-ai/baseline-status?test_name=${testName}`);
  }

  // ============================================================================
  // Project Management Endpoints
  // ============================================================================

  /**
   * Create new project
   */
  async createProject(name: string, description?: string, environment?: string): Promise<{ project: Project }> {
    return this.request('POST', '/api/projects', {
      name,
      description,
      environment: environment || 'Development',
    });
  }

  /**
   * List all projects
   */
  async listProjects(): Promise<{ projects: Project[] }> {
    return this.request('GET', '/api/projects');
  }

  /**
   * Get project details
   */
  async getProject(projectId: string): Promise<{ project: Project }> {
    return this.request('GET', `/api/projects/${projectId}`);
  }

  /**
   * Update project
   */
  async updateProject(
    projectId: string,
    updates: Partial<Project>
  ): Promise<{ project: Project }> {
    return this.request('PUT', `/api/projects/${projectId}`, updates);
  }

  /**
   * Delete project
   */
  async deleteProject(projectId: string): Promise<{ success: boolean }> {
    return this.request('DELETE', `/api/projects/${projectId}`);
  }

  // ============================================================================
  // Health Check
  // ============================================================================

  /**
   * Check API health status
   */
  async healthCheck(): Promise<{ status: string; version: string }> {
    try {
      return await this.request('GET', '/api/health');
    } catch (error) {
      throw new Error('API server is unavailable');
    }
  }
}

export default APIClient;
