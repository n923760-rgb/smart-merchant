import type { Journal } from "./accounting";
import { SessionError } from "./session";

export type JournalDraft = {
  branch_id: string | null;
  booking_date: string;
  description: string;
  lines: {
    account_id: string;
    debit: string;
    credit: string;
    description: string | null;
  }[];
};
export type JournalPayload = JournalDraft & { request_id: string };
export type CommandScope = {
  userId: string;
  organizationId: string;
  branchId: string | null;
};
export type PendingJournal = {
  version: 1;
  userId: string;
  organizationId: string;
  payload: JournalPayload;
};
type Store = Pick<Storage, "getItem" | "setItem" | "removeItem">;
type Transport = <T>(path: string, init?: RequestInit) => Promise<T>;
type Lock = <T>(name: string, action: () => Promise<T>) => Promise<T>;
export class JournalProblem extends Error {
  constructor(
    public code: "invalid" | "storage" | "pending" | "response" | "missing",
    message = code,
  ) {
    super(message);
  }
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function validId(value: unknown): value is string {
  return typeof value === "string" && uuid.test(value);
}
export function journalCents(value: string): bigint {
  // Convert digit strings to integer cents. No monetary Number/parseFloat coercion.
  if (typeof value !== "string" || !/^\d{1,16}(?:\.\d{1,2})?$/.test(value))
    throw new JournalProblem("invalid");
  const [whole, part = ""] = value.split(".");
  return BigInt(whole) * BigInt(100) + BigInt(part.padEnd(2, "0"));
}
export function centsAmount(value: bigint): string {
  return (
    (value / BigInt(100)).toString() +
    "." +
    (value % BigInt(100)).toString().padStart(2, "0")
  );
}
export function journalTotals(draft: JournalDraft): {
  debit: string;
  credit: string;
} {
  let debit = BigInt(0),
    credit = BigInt(0);
  for (const line of draft.lines) {
    debit += journalCents(line.debit);
    credit += journalCents(line.credit);
  }
  return { debit: centsAmount(debit), credit: centsAmount(credit) };
}
export function normalizeJournal(draft: JournalDraft): JournalDraft {
  if (
    !draft ||
    (draft.branch_id !== null && !validId(draft.branch_id)) ||
    typeof draft.booking_date !== "string" ||
    !/^\d{4}-\d{2}-\d{2}$/.test(draft.booking_date) ||
    typeof draft.description !== "string" ||
    !draft.description.trim() ||
    Array.from(draft.description.trim()).length > 500 ||
    !Array.isArray(draft.lines) ||
    draft.lines.length < 2 ||
    draft.lines.length > 100
  )
    throw new JournalProblem("invalid");
  const date = new Date(draft.booking_date + "T00:00:00Z");
  if (
    !Number.isFinite(date.getTime()) ||
    date.toISOString().slice(0, 10) !== draft.booking_date
  )
    throw new JournalProblem("invalid");
  const lines = draft.lines.map((line) => {
    if (
      !line ||
      !validId(line.account_id) ||
      (line.description !== null && typeof line.description !== "string") ||
      (line.description !== null &&
        Array.from(line.description.trim()).length > 500)
    )
      throw new JournalProblem("invalid");
    const debit = journalCents(line.debit === "" ? "0" : line.debit);
    const credit = journalCents(line.credit === "" ? "0" : line.credit);
    if (debit > BigInt(0) === credit > BigInt(0))
      throw new JournalProblem("invalid");
    return {
      account_id: line.account_id,
      debit: centsAmount(debit),
      credit: centsAmount(credit),
      description: line.description?.trim() || null,
    };
  });
  const result = {
    branch_id: draft.branch_id,
    booking_date: draft.booking_date,
    description: draft.description.trim(),
    lines,
  };
  const totals = journalTotals(result);
  if (totals.debit !== totals.credit) throw new JournalProblem("invalid");
  return result;
}
export function journalStorageKey(scope: CommandScope): string {
  if (
    !validId(scope.userId) ||
    !validId(scope.organizationId) ||
    (scope.branchId !== null && !validId(scope.branchId))
  )
    throw new JournalProblem("invalid");
  return (
    "smart-merchant:journal:v1:" +
    scope.userId +
    ":" +
    scope.organizationId +
    ":" +
    (scope.branchId ?? "organization")
  );
}
export function readPendingJournal(
  store: Store,
  scope: CommandScope,
): PendingJournal | null {
  try {
    const raw = store.getItem(journalStorageKey(scope));
    if (raw === null) return null;
    if (raw.length > 100_000) throw new Error("Oversized pending command");
    const saved = JSON.parse(raw) as PendingJournal;
    if (
      saved.version !== 1 ||
      saved.userId !== scope.userId ||
      saved.organizationId !== scope.organizationId ||
      !validId(saved.payload?.request_id) ||
      saved.payload.branch_id !== scope.branchId
    )
      throw new Error("Pending command scope mismatch");
    const canonical = {
      ...normalizeJournal(saved.payload),
      request_id: saved.payload.request_id,
    };
    if (JSON.stringify(saved.payload) !== JSON.stringify(canonical))
      throw new Error("Invalid pending command");
    return saved;
  } catch {
    // Never erase an unreadable/foreign pending command or silently allow a new one.
    throw new JournalProblem("storage");
  }
}
function verifiedJournal(value: unknown, pending: PendingJournal): Journal {
  const result = value as Journal;
  const body = pending.payload;
  const totals = journalTotals(body);
  if (
    !result ||
    !validId(result.id) ||
    result.status !== "POSTED" ||
    result.organization_id !== pending.organizationId ||
    result.branch_id !== body.branch_id ||
    result.request_id !== body.request_id ||
    result.currency !== "SAR" ||
    result.reversal_of_id !== null ||
    result.posted_by !== pending.userId ||
    typeof result.posted_at !== "string" ||
    !Number.isFinite(Date.parse(result.posted_at)) ||
    result.booking_date !== body.booking_date ||
    result.description !== body.description ||
    result.total_debit !== totals.debit ||
    result.total_credit !== totals.credit ||
    !Array.isArray(result.lines) ||
    result.lines.length !== body.lines.length ||
    result.lines.some(
      (line, i) =>
        !line ||
        line.line_number !== i + 1 ||
        line.account_id !== body.lines[i].account_id ||
        line.debit !== body.lines[i].debit ||
        line.credit !== body.lines[i].credit ||
        line.description !== body.lines[i].description,
    )
  )
    throw new JournalProblem("response");
  return result;
}

// Cooperative tabs serialize the whole save/send/clear protocol using Web Locks.
// A restored record is always uncertain; a lookup 404 never authorizes abandoning it.
export class JournalCommands {
  readonly key: string;
  constructor(
    readonly scope: CommandScope,
    private store: Store,
    private request: Transport,
    private lock: Lock,
    private checkContext: () => void,
    private newId: () => string,
  ) {
    this.key = journalStorageKey(scope);
  }
  pending(): PendingJournal | null {
    return readPendingJournal(this.store, this.scope);
  }
  private save(pending: PendingJournal): void {
    try {
      this.store.setItem(this.key, JSON.stringify(pending));
      if (this.store.getItem(this.key) !== JSON.stringify(pending))
        throw new Error("Storage mismatch");
    } catch {
      throw new JournalProblem("storage");
    }
  }
  private clear(pending: PendingJournal): void {
    const current = this.pending();
    if (!current || JSON.stringify(current) !== JSON.stringify(pending))
      throw new JournalProblem("storage");
    try {
      this.store.removeItem(this.key);
    } catch {
      throw new JournalProblem("storage");
    }
  }
  private async send(pending: PendingJournal): Promise<Journal> {
    const response = await this.request<unknown>("accounting/journals", {
      method: "POST",
      body: JSON.stringify(pending.payload),
    });
    this.checkContext();
    const result = verifiedJournal(response, pending);
    this.clear(pending);
    return result;
  }
  async confirm(draft: JournalDraft): Promise<Journal> {
    // Copy the preview before waiting on another tab; never read later mutable form state.
    const body = normalizeJournal(draft);
    if (body.branch_id !== this.scope.branchId)
      throw new JournalProblem("invalid");
    this.checkContext();
    return this.lock(this.key, async () => {
      this.checkContext();
      if (this.pending()) throw new JournalProblem("pending");
      const requestId = this.newId();
      if (!validId(requestId)) throw new JournalProblem("invalid");
      const pending: PendingJournal = {
        version: 1,
        userId: this.scope.userId,
        organizationId: this.scope.organizationId,
        payload: { ...body, request_id: requestId },
      };
      this.save(pending); // This must succeed before the first network side effect.
      try {
        return await this.send(pending);
      } catch (error) {
        // Only a first, explicit validation/permission rejection permits editing.
        // Conflict, timeout, context change, malformed success and any restored/retried
        // command remain pending. A retry's rejection cannot negate an earlier commit.
        if (
          error instanceof SessionError &&
          [400, 403, 404, 413, 422].includes(error.status)
        ) {
          this.checkContext();
          this.clear(pending);
        }
        throw error;
      }
    });
  }
  async reconcile(): Promise<Journal | null> {
    this.checkContext();
    return this.lock(this.key, async () => {
      this.checkContext();
      const pending = this.pending();
      if (!pending) throw new JournalProblem("missing");
      const params =
        pending.payload.branch_id === null
          ? ""
          : "?branch_id=" + encodeURIComponent(pending.payload.branch_id);
      let response;
      try {
        response = await this.request<unknown>(
          "accounting/journal-requests/" + pending.payload.request_id + params,
        );
      } catch (error) {
        this.checkContext();
        if (error instanceof SessionError && error.status === 404) return null;
        throw error;
      }
      this.checkContext();
      const result = verifiedJournal(response, pending);
      this.clear(pending);
      return result;
    });
  }
  async resend(): Promise<Journal> {
    this.checkContext();
    return this.lock(this.key, async () => {
      this.checkContext();
      const pending = this.pending();
      if (!pending) throw new JournalProblem("missing");
      return this.send(pending); // Exact stored body and UUID; never a new request.
    });
  }
}
