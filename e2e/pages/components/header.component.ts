import { type Page, type Locator, expect } from "@playwright/test";

export class HeaderComponent {
  private readonly header: Locator;

  constructor(private readonly page: Page) {
    this.header = page.locator("header");
  }

  get userMenuButton() {
    return this.page.getByTestId("header-btn-user-menu");
  }

  get profileLink() {
    return this.page.getByTestId("user-menu-link-profile");
  }

  get infoLink() {
    return this.page.getByTestId("user-menu-link-info");
  }

  get logoutLink() {
    return this.page.getByTestId("user-menu-btn-logout");
  }

  async openUserMenu() {
    await this.userMenuButton.click();
  }

  async goToProfile() {
    await this.openUserMenu();
    await this.profileLink.click();
  }

  async logout() {
    await this.openUserMenu();
    await this.logoutLink.click();
  }
}
