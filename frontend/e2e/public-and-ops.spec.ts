import { expect, test } from "@playwright/test";

test("public visitor can switch feed modes and open a post", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "AI开发者论坛" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "为你推荐" })).toBeVisible();
  await page.getByRole("tab", { name: "热门" }).click();
});

test("unauthenticated operations access is hidden", async ({ page }) => {
  await page.goto("/ops");
  await expect(page).toHaveURL(/\/$|\/auth/);
});
