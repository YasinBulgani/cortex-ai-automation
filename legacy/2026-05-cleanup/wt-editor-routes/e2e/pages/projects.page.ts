import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ProjectsPage extends BasePage {
  readonly url = "/projects";

  // ── Locators ───────────────────────────────────────────────────────────────
  get heading() {
    // "Projeler" birden fazla yerde (sidebar link, header, açıklama) geçiyor;
    // strict locator ihlalini önlemek için sidebar link'i tercih ediyoruz:
    // bu etiket her zaman layout seviyesinde render olur ve yüklendiğini gösterir.
    return this.page.locator("[data-testid='sidebar-link-projects']");
  }
  get nameInput() {
    return this.placeholder("Örn. Ödeme API");
  }
  get descInput() {
    return this.placeholder("Kısa açıklama");
  }
  get createButton() {
    return this.role("button", { name: "Oluştur" });
  }
  get emptyState() {
    return this.text("Henüz proje yok");
  }

  projectCard(name: string) {
    return this.role("link", { name });
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async createProject(name: string, description?: string) {
    await this.nameInput.fill(name);
    if (description) {
      await this.descInput.fill(description);
    }
    await this.createButton.click();
  }

  async clickProject(name: string) {
    await this.projectCard(name).click();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertProjectVisible(name: string) {
    await expect(this.text(name)).toBeVisible();
  }

  async assertPageLoaded() {
    await expect(this.heading).toBeVisible();
  }
}
