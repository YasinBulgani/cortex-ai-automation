/**
 * Karantina mekanizması: bilinen flaky testleri Allure'da işaretler,
 * CI gate'ini kırmadan retry sonucu "known_flaky" olarak raporlar.
 *
 * Kullanım:
 *   import { quarantinedTest as test, markAsFlaky } from "../utils/quarantine";
 *
 *   test("flaky senaryo", async ({ page }, testInfo) => {
 *     markAsFlaky(testInfo, "Ağ gecikmesine duyarlı — #1234 bekliyor");
 *     ...
 *   });
 *
 * Veya quarantine.json'a ekle, test normal `test` ile yazılmaya devam eder —
 * beforeEach otomatik olarak Allure annotation'ı ekler.
 */

import { test as baseTest, type TestInfo } from "@playwright/test";
import registry from "../quarantine.json";

interface QuarantineEntry {
  testTitle: string;
  file: string;
  reason: string;
  since: string;
  owner?: string;
  expiresAfter?: string;
}

const today = new Date().toISOString().split("T")[0];

function findEntry(title: string): QuarantineEntry | undefined {
  return (registry as { entries: QuarantineEntry[] }).entries.find(
    (e) =>
      title === e.testTitle ||
      title.includes(e.testTitle) ||
      e.testTitle.includes(title)
  );
}

function isExpired(entry: QuarantineEntry): boolean {
  return !!entry.expiresAfter && entry.expiresAfter < today;
}

/** Inline flaky marker — registry gerektirmez, testInfo içinden çağır. */
export function markAsFlaky(testInfo: TestInfo, reason: string): void {
  testInfo.annotations.push({ type: "known_flaky", description: reason });
}

/**
 * Registry tabanlı quarantine — quarantine.json'daki entry ile eşleşen
 * testlere otomatik Allure annotation ekler.
 */
export const quarantinedTest = baseTest.extend<Record<string, never>>({});

quarantinedTest.beforeEach(async ({}, testInfo) => {
  const entry = findEntry(testInfo.title);
  if (!entry || isExpired(entry)) return;

  testInfo.annotations.push({
    type: "known_flaky",
    description: `Quarantined: ${entry.reason} (since ${entry.since})`,
  });
  if (entry.owner) {
    testInfo.annotations.push({ type: "owner", description: entry.owner });
  }
});

export { findEntry, isExpired };
export type { QuarantineEntry };
