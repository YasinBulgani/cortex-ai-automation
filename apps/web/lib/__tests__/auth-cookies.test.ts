import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE } from "@/lib/auth-cookies";

describe("auth-cookies constants", () => {
  it("access token cookie name is defined", () => {
    expect(ACCESS_TOKEN_COOKIE).toBe("bgts_access_token");
  });

  it("refresh token cookie name is defined", () => {
    expect(REFRESH_TOKEN_COOKIE).toBe("bgts_refresh_token");
  });

  it("cookie names do not contain special characters", () => {
    const valid = /^[a-zA-Z0-9_]+$/;
    expect(ACCESS_TOKEN_COOKIE).toMatch(valid);
    expect(REFRESH_TOKEN_COOKIE).toMatch(valid);
  });

  it("cookie names are distinct", () => {
    expect(ACCESS_TOKEN_COOKIE).not.toBe(REFRESH_TOKEN_COOKIE);
  });
});
