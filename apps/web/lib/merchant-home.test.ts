import { describe, expect, it } from "vitest";
import type { AuthorizationContext } from "./permissions";
import { merchantActivityLabel, merchantHomeActions } from "./merchant-home";

function context(
  permissions: string[] = [],
  branch_permissions: Record<string, string[]> = {},
): AuthorizationContext {
  return {
    organization: { id: "org", name: "Example" },
    permissions,
    branch_permissions,
  };
}

describe("merchant home permission-scoped actions", () => {
  it("never offers unsupported or unauthorized navigation", () => {
    expect(merchantHomeActions(context())).toEqual([]);
  });

  it("offers only branch-visible operations without global management", () => {
    expect(
      merchantHomeActions(context([], { abha: ["branches.read"] })).map((item) => item.href),
    ).toEqual(["/branches"]);
  });

  it("retains accountant-only navigation even without organization dashboard access", () => {
    expect(
      merchantHomeActions(context([], { abha: ["accounting.journals.read"] })).map(
        (item) => item.href,
      ),
    ).toEqual(["/accounting"]);
  });

  it("offers existing real application routes to fully privileged owners", () => {
    expect(
      merchantHomeActions(
        context([
          "accounting.accounts.read",
          "branches.read",
          "users.read",
          "terminals.read",
        ]),
      ).map((item) => item.href),
    ).toEqual(["/accounting", "/branches", "/users", "/devices"]);
  });

  it("labels known admin activity and preserves unknown event type", () => {
    expect(merchantActivityLabel("BRANCH_CREATED")).toBe("إضافة فرع");
    expect(merchantActivityLabel("SOMETHING_NEW")).toBe("SOMETHING NEW");
  });
});
