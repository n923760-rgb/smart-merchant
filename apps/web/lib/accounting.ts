import { canAccess, type AuthorizationContext } from "./permissions";

export const accountingReads = [
  "accounting.accounts.read",
  "accounting.journals.read",
] as const;
export type AccountingRead = (typeof accountingReads)[number];
export type AccountingScope = { id: string; branchId: string | null };
export type Account = {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  account_type: "ASSET" | "LIABILITY" | "EQUITY" | "REVENUE" | "EXPENSE";
  is_active: boolean;
};
export type Journal = {
  id: string;
  organization_id: string;
  branch_id: string | null;
  request_id: string;
  booking_date: string;
  description: string;
  currency: string;
  status: "POSTED";
  reversal_of_id: string | null;
  posted_by: string;
  posted_at: string;
  total_debit: string;
  total_credit: string;
  lines: {
    account_id: string;
    line_number: number;
    debit: string;
    credit: string;
    description: string | null;
  }[];
};

export function canReadAccounting(
  context: AuthorizationContext,
  code: AccountingRead,
  branchId: string | null,
): boolean {
  return (
    context.permissions.includes(code) ||
    (branchId !== null &&
      (context.branch_permissions[branchId] ?? []).includes(code))
  );
}

export function accountingScopes(
  context: AuthorizationContext,
): AccountingScope[] {
  const scopes: AccountingScope[] = [];
  if (accountingReads.some((code) => context.permissions.includes(code)))
    scopes.push({ id: "organization", branchId: null });
  for (const id of Object.keys(context.branch_permissions).sort()) {
    if (
      accountingReads.some((code) =>
        context.branch_permissions[id].includes(code),
      )
    )
      scopes.push({ id, branchId: id });
  }
  return scopes;
}

export function accountingLanding(
  context: AuthorizationContext,
  pathname: string,
): string | null {
  return pathname === "/overview" &&
    !canAccess(context, "organization.read") &&
    accountingScopes(context).length > 0
    ? "/accounting"
    : null;
}

export function accountingListPath(
  resource: "accounts" | "journals",
  branchId: string | null,
  page: number,
): string {
  if (!Number.isSafeInteger(page) || page < 1)
    throw new Error("Invalid accounting page");
  const params = new URLSearchParams({ page: String(page), page_size: "20" });
  if (branchId !== null) params.set("branch_id", branchId);
  return `accounting/${resource}?${params}`;
}

// Preserve every digit, including amounts beyond JavaScript's safe integer limit.
// Backend Decimal strings are authoritative; no browser aggregation/float rounding.
export function accountingAmount(value: string): string {
  if (typeof value !== "string" || !/^\d+(?:\.\d{1,2})?$/.test(value))
    return "—";
  const [integer, fraction = ""] = value.split(".");
  return `${integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${fraction.padEnd(2, "0")}`;
}
