import { type Page, type Locator, expect } from "@playwright/test";
import { findElement, type LocatorResult } from "../utils/ai-locator";
import { resolveFromRepo, validateLocators } from "../utils/locator-bridge";

export abstract class BasePage {
  constructor(protected readonly page: Page) {}

  abstract readonly url: string | RegExp;

  async goto() {
    if (typeof this.url === "string") {
      await this.page.goto(this.url, { waitUntil: "domcontentloaded" });
    }
  }

  async waitForReady() {
    await this.page.waitForLoadState("domcontentloaded");
  }

  async assertUrlMatches(pattern?: RegExp) {
    await expect(this.page).toHaveURL(pattern ?? this.url);
  }

  protected testId(id: string): Locator {
    return this.page.getByTestId(id);
  }

  protected role(
    role: Parameters<Page["getByRole"]>[0],
    options?: Parameters<Page["getByRole"]>[1]
  ): Locator {
    return this.page.getByRole(role, options);
  }

  protected label(text: string): Locator {
    return this.page.getByLabel(text);
  }

  protected text(text: string | RegExp): Locator {
    return this.page.getByText(text);
  }

  protected placeholder(text: string): Locator {
    return this.page.getByPlaceholder(text);
  }

  /**
   * Resolve an element from the central locator repository (engine/locators/locator_repository.json).
   * Falls back to testId if the element is not found in the repository.
   */
  protected fromRepo(pageName: string, elementName: string): Locator {
    const loc = resolveFromRepo(this.page, pageName, elementName);
    if (loc) return loc;
    return this.page.getByTestId(elementName);
  }

  /**
   * Validate all locators for a page against the current DOM.
   * Useful for CI health checks.
   */
  async checkLocatorHealth(pageName: string) {
    return validateLocators(this.page, pageName);
  }

  /**
   * AI-enhanced element finder.
   * 6 strateji zinciri: testId -> role -> label -> text -> AI-LLM -> CSS
   */
  protected async findByIntent(
    intent: string,
    options?: { role?: string; fallbackCss?: string },
  ): Promise<Locator> {
    const result = await findElement(this.page, intent, options);
    return result.locator;
  }
}
