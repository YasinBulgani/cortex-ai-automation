export class AppError extends Error {
  constructor(
    public code: string,
    message: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'AppError';
  }
}

export const getErrorMessage = (error: any): string => {
  if (error instanceof AppError) {
    return error.message;
  }

  if (error.response?.data?.message) {
    return error.response.data.message;
  }

  if (error.message) {
    return error.message;
  }

  return 'An unexpected error occurred';
};

export const getErrorCode = (error: any): string => {
  if (error instanceof AppError) {
    return error.code;
  }

  if (error.response?.status) {
    return `HTTP_${error.response.status}`;
  }

  return 'UNKNOWN_ERROR';
};

export const isNetworkError = (error: any): boolean => {
  return error.message === 'Network Error' || error.code === 'ECONNABORTED';
};

export const isAuthError = (error: any): boolean => {
  const code = getErrorCode(error);
  return code === 'HTTP_401' || code === 'HTTP_403';
};

export const isNotFoundError = (error: any): boolean => {
  return getErrorCode(error) === 'HTTP_404';
};

export const isValidationError = (error: any): boolean => {
  return getErrorCode(error) === 'HTTP_422' || getErrorCode(error) === 'HTTP_400';
};

export const handleApiError = (error: any): AppError => {
  const message = getErrorMessage(error);
  const code = getErrorCode(error);
  const statusCode = error.response?.status;

  console.error(`API Error [${code}]: ${message}`, error);

  return new AppError(code, message, statusCode, error.response?.data);
};

export const logError = (error: any, context?: string) => {
  const timestamp = new Date().toISOString();
  const message = getErrorMessage(error);
  const code = getErrorCode(error);

  console.error(
    `[${timestamp}] ${context || 'Error'} - [${code}]: ${message}`,
    error
  );

  // In production, send to error tracking service (Sentry, etc.)
  if (__DEV__ === false) {
    // captureException(error, { tags: { code, context } });
  }
};
