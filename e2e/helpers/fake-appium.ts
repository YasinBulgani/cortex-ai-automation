import http, { type IncomingMessage, type ServerResponse } from "node:http";
import type { AddressInfo } from "node:net";

const ONE_BY_ONE_PNG =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";

export class FakeAppiumServer {
  private server?: http.Server;
  readonly requests: string[] = [];
  readonly sessionId = "fake-session";

  async start(): Promise<string> {
    this.server = http.createServer((req, res) => {
      void this.handle(req, res);
    });

    await new Promise<void>((resolve) => {
      this.server?.listen(0, "127.0.0.1", resolve);
    });

    const address = this.server.address() as AddressInfo;
    return `http://127.0.0.1:${address.port}`;
  }

  async stop(): Promise<void> {
    if (!this.server) return;
    await new Promise<void>((resolve, reject) => {
      this.server?.close((error) => {
        if (error) reject(error);
        else resolve();
      });
    });
    this.server = undefined;
  }

  private async handle(req: IncomingMessage, res: ServerResponse): Promise<void> {
    const method = req.method ?? "GET";
    const path = req.url ?? "/";
    this.requests.push(`${method} ${path}`);
    await drain(req);

    if (method === "GET" && path === "/status") {
      return json(res, 200, { value: { ready: true, message: "fake appium ready" } });
    }
    if (method === "POST" && path === "/session") {
      return json(res, 200, {
        value: {
          sessionId: this.sessionId,
          capabilities: { platformName: "Android", automationName: "UiAutomator2" },
        },
      });
    }
    if (method === "POST" && path === `/session/${this.sessionId}/url`) {
      return json(res, 200, { value: null });
    }
    if (method === "GET" && path === `/session/${this.sessionId}/screenshot`) {
      return json(res, 200, { value: ONE_BY_ONE_PNG });
    }
    if (method === "GET" && path === `/session/${this.sessionId}/source`) {
      return json(res, 200, {
        value: "<AppiumFake><Screen name=\"home\"><Text>Neurex Mobile Smoke</Text></Screen></AppiumFake>",
      });
    }
    if (method === "DELETE" && path === `/session/${this.sessionId}`) {
      return json(res, 200, { value: null });
    }

    return json(res, 404, {
      value: {
        error: "unknown command",
        message: `Fake Appium route not implemented: ${method} ${path}`,
      },
    });
  }
}

function json(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

async function drain(req: IncomingMessage): Promise<void> {
  for await (const _chunk of req) {
    // Consume request body so Node can reuse the socket cleanly.
  }
}
