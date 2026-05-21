import { test as base, expect, type Page, type Locator } from "@playwright/test";
import { TestDataFactory } from "./test-data";
import { API_BASE } from "../config/runtime";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "../config/auth";
import {
  findWithHealing,
  createLocatorCandidates,
  getHealingHistory,
  clearHealingHistory,
  type LocatorCandidate,
} from "../helpers/self-healing-locator";

const API = API_BASE;

interface SelfHealingHelper {
  find(elementId: string, candidates: LocatorCandidate[]): Promise<Locator>;
  candidates: typeof createLocatorCandidates;
  history(): ReturnType<typeof getHealingHistory>;
}

type TestFixtures = {
  factory: TestDataFactory;
  adminToken: string;
  selfHeal: SelfHealingHelper;
};

export const test = base.extend<TestFixtures>({
  factory: async ({ request }, use) => {
    const loginRes = await request.post(`${API}/api/v1/auth/login`, {
      data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
    });
    const { access_token: token } = await loginRes.json();
    const factory = new TestDataFactory(request, token);
    await use(factory);
    await factory.cleanup();
  },

  adminToken: async ({ request }, use) => {
    const res = await request.post(`${API}/api/v1/auth/login`, {
      data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
    });
    const { access_token: token } = await res.json();
    await use(token);
  },

  selfHeal: async ({ page }, use) => {
    clearHealingHistory();
    const helper: SelfHealingHelper = {
      find: (elementId, candidates) => findWithHealing(page, elementId, candidates),
      candidates: createLocatorCandidates,
      history: getHealingHistory,
    };
    await use(helper);
  },
});

export { expect };
export type { LocatorCandidate };
