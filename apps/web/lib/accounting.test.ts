import { describe, expect, it } from "vitest";
import {
  accountingAmount,
  accountingLanding,
  accountingListPath,
  accountingScopes,
  canReadAccounting,
  canPostAccounting,
} from "./accounting";
import type { AuthorizationContext } from "./permissions";

const context = (
  permissions: string[] = [],
  branch_permissions: Record<string, string[]> = {},
): AuthorizationContext => ({
  organization: { id: "merchant", name: "Services" },
  permissions,
  branch_permissions,
});

describe("accounting authorization and scope", () => {
  it("does not infer posting from reads and keeps branch posting scoped", () => {
    expect(canPostAccounting(context(["accounting.journals.read"]), null)).toBe(
      false,
    );
    const ctx = context([], { B: ["accounting.journals.post"] });
    expect(canPostAccounting(ctx, "B")).toBe(true);
    expect(canPostAccounting(ctx, "C")).toBe(false);
    expect(canPostAccounting(ctx, null)).toBe(false);
    expect(canReadAccounting(ctx, "accounting.journals.read", "B")).toBe(false);
    expect(accountingLanding(ctx, "/overview")).toBe("/accounting");
    expect(accountingScopes(ctx)).toEqual([{ id: "B", branchId: "B" }]);
  });
  it("allows accounting without a POS grant, terminal or shift", () => {
    const ctx = context([
      "accounting.accounts.read",
      "accounting.journals.read",
    ]);
    expect(accountingScopes(ctx)).toEqual([
      { id: "organization", branchId: null },
    ]);
    expect(canReadAccounting(ctx, "accounting.journals.read", null)).toBe(true);
  });
  it("never upgrades a branch grant to organization or another branch", () => {
    const ctx = context([], {
      B: ["accounting.journals.read"],
      A: ["accounting.accounts.read"],
      C: ["branches.read"],
    });
    expect(accountingScopes(ctx)).toEqual([
      { id: "A", branchId: "A" },
      { id: "B", branchId: "B" },
    ]);
    expect(canReadAccounting(ctx, "accounting.journals.read", null)).toBe(
      false,
    );
    expect(canReadAccounting(ctx, "accounting.journals.read", "A")).toBe(false);
    expect(canReadAccounting(ctx, "accounting.journals.read", "B")).toBe(true);
    expect(canReadAccounting(ctx, "accounting.journals.read", "C")).toBe(false);
  });
  it("qualifies each resource independently and exposes no accounting for a cashier", () => {
    const ctx = context(["accounting.accounts.read"], {
      B: ["accounting.journals.read"],
    });
    expect(canReadAccounting(ctx, "accounting.accounts.read", null)).toBe(true);
    expect(canReadAccounting(ctx, "accounting.journals.read", null)).toBe(
      false,
    );
    expect(canReadAccounting(ctx, "accounting.accounts.read", "B")).toBe(true);
    expect(
      accountingScopes(context(["terminals.read", "branches.read"])),
    ).toEqual([]);
  });
  it("gives accounting-only users a working landing without unrelated organization/POS grants", () => {
    expect(
      accountingLanding(context(["accounting.journals.read"]), "/overview"),
    ).toBe("/accounting");
    expect(
      accountingLanding(
        context([], { B: ["accounting.accounts.read"] }),
        "/overview",
      ),
    ).toBe("/accounting");
    expect(
      accountingLanding(
        context(["organization.read", "accounting.journals.read"]),
        "/overview",
      ),
    ).toBeNull();
    expect(
      accountingLanding(context(["accounting.journals.read"]), "/users"),
    ).toBeNull();
    expect(accountingLanding(context(), "/overview")).toBeNull();
  });
});

describe("accounting read requests", () => {
  it("binds every branch resource request explicitly and safely encodes it", () => {
    expect(accountingListPath("accounts", "branch&other", 2)).toBe(
      "accounting/accounts?page=2&page_size=20&branch_id=branch%26other",
    );
    expect(accountingListPath("journals", null, 1)).toBe(
      "accounting/journals?page=1&page_size=20",
    );
  });
  it.each([0, -1, 1.5, Number.POSITIVE_INFINITY])(
    "rejects invalid page %s",
    (page) => {
      expect(() => accountingListPath("accounts", null, page)).toThrow();
    },
  );
});

describe("lossless accounting amount presentation", () => {
  it("retains exact large values and cents rather than using binary floats", () => {
    expect(accountingAmount("9007199254740993.01")).toBe(
      "9,007,199,254,740,993.01",
    );
    expect(accountingAmount("9999999999999999.99")).toBe(
      "9,999,999,999,999,999.99",
    );
    expect(accountingAmount("0.10")).toBe("0.10");
    expect(accountingAmount("0")).toBe("0.00");
    expect(accountingAmount("100.3")).toBe("100.30");
  });
  it.each(["NaN", "Infinity", "-1", "1e4", "1.001", "", "0<script>", " 1 "])(
    "does not misrepresent malformed value %s as zero",
    (value) => {
      expect(accountingAmount(value)).toBe("—");
    },
  );
});
