// Sentry — Browser (Client) konfigürasyonu
// @sentry/nextjs kurulu degilse sessizce atlanir

{
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

  if (dsn) {
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const Sentry = require("@sentry/nextjs");
      Sentry.init({
        dsn,
        environment: process.env.NODE_ENV,
        tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
        replaysOnErrorSampleRate: 1.0,
        replaysSessionSampleRate: 0.1,
        integrations: [
          Sentry.replayIntegration({
            maskAllInputs: true,
            blockAllMedia: false,
          }),
        ],
        sendDefaultPii: false,
      });
    } catch {
      // @sentry/nextjs kurulu degil — sessizce atla
    }
  }
}

export {};
