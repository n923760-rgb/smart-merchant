import { describe, expect, it, vi } from "vitest";
import {
  JournalCommands,
  JournalProblem,
  journalCents,
  journalStorageKey,
  journalTotals,
  normalizeJournal,
  readPendingJournal,
  type CommandScope,
  type JournalDraft,
  type JournalPayload,
} from "./journal-command";
import { SessionError } from "./session";

const user = "10000000-0000-4000-8000-000000000001";
const org = "10000000-0000-4000-8000-000000000002";
const branch = "10000000-0000-4000-8000-000000000003";
const requestId = "10000000-0000-4000-8000-000000000004";
const account = "10000000-0000-4000-8000-000000000005";
const revenue = "10000000-0000-4000-8000-000000000006";
const entry = "10000000-0000-4000-8000-000000000007";
const scope: CommandScope = {
  userId: user,
  organizationId: org,
  branchId: null,
};
function draft(amount = "100.00"): JournalDraft {
  return {
    branch_id: null,
    booking_date: "2026-10-07",
    description: " Service ",
    lines: [
      { account_id: account, debit: amount, credit: "", description: null },
      {
        account_id: revenue,
        debit: "",
        credit: amount,
        description: " Revenue ",
      },
    ],
  };
}
function response(body: JournalPayload) {
  const totals = journalTotals(body);
  return {
    id: entry,
    organization_id: org,
    branch_id: body.branch_id,
    request_id: body.request_id,
    booking_date: body.booking_date,
    description: body.description,
    currency: "SAR",
    status: "POSTED",
    reversal_of_id: null,
    posted_by: user,
    posted_at: "2026-10-07T08:00:00Z",
    total_debit: totals.debit,
    total_credit: totals.credit,
    lines: body.lines.map((line, i) => ({ ...line, line_number: i + 1 })),
  };
}
function fixture(selectedScope = scope) {
  const data = new Map<string, string>();
  const store = {
    getItem: vi.fn((key: string) => data.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => {
      data.set(key, value);
    }),
    removeItem: vi.fn((key: string) => {
      data.delete(key);
    }),
  };
  const newId = vi.fn(() => requestId);
  const context = vi.fn();
  const locked = new Set<string>();
  const lock = async <T>(
    name: string,
    action: () => Promise<T>,
  ): Promise<T> => {
    if (locked.has(name)) throw new JournalProblem("pending");
    locked.add(name);
    try {
      return await action();
    } finally {
      locked.delete(name);
    }
  };
  const request = vi.fn(
    async (_path: string, init?: RequestInit): Promise<unknown> =>
      response(JSON.parse(init!.body as string)),
  );
  const manager = () =>
    new JournalCommands(
      selectedScope,
      store,
      request as <T>(path: string, init?: RequestInit) => Promise<T>,
      lock,
      context,
      newId,
    );
  return { data, store, newId, context, request, manager };
}

describe("exact journal input and preview", () => {
  it("adds cents beyond the safe integer limit and canonicalizes all sides", () => {
    const result = normalizeJournal(draft("9007199254740993.01"));
    expect(result.description).toBe("Service");
    expect(result.lines[0].credit).toBe("0.00");
    expect(result.lines[1].description).toBe("Revenue");
    expect(journalTotals(result)).toEqual({
      debit: "9007199254740993.01",
      credit: "9007199254740993.01",
    });
    expect(journalCents("9999999999999999.99")).toBe(
      BigInt("999999999999999999"),
    );
    expect(normalizeJournal(draft("0001.2")).lines[0].debit).toBe("1.20");
  });
  it("calculates a many-line total beyond the individual amount bound without losing cents", () => {
    const source = draft("9999999999999999.99");
    source.lines = [...source.lines, ...source.lines];
    expect(journalTotals(normalizeJournal(source)).debit).toBe(
      "19999999999999999.98",
    );
  });
  it.each([
    "NaN",
    "Infinity",
    "-1",
    "1e2",
    "1.001",
    "10000000000000000",
    " 1",
    "1,000",
    "",
  ])("rejects malformed amount %s", (amount) =>
    expect(() => journalCents(amount)).toThrow(),
  );
  it.each(["2026-02-29", "2026-04-31", "07/10/2026", "invalid"])(
    "rejects invalid booking date %s",
    (booking_date) =>
      expect(() => normalizeJournal({ ...draft(), booking_date })).toThrow(),
  );
  it("rejects imbalance, both sides, empty lines, bad identities and excessive rows", () => {
    const bad = draft();
    bad.lines[0].debit = "100.01";
    expect(() => normalizeJournal(bad)).toThrow();
    bad.lines[0].credit = "1.00";
    expect(() => normalizeJournal(bad)).toThrow();
    expect(() => normalizeJournal(draft("0"))).toThrow();
    expect(() => normalizeJournal({ ...draft(), lines: [] })).toThrow();
    expect(() => normalizeJournal({ ...draft(), description: " " })).toThrow();
    expect(() =>
      normalizeJournal({ ...draft(), branch_id: "foreign" }),
    ).toThrow();
    expect(() =>
      normalizeJournal({
        ...draft(),
        lines: Array(102).fill(draft().lines[0]),
      }),
    ).toThrow();
  });
});

describe("confirmed durable journal commands", () => {
  it("persists the exact confirmed payload before dispatch and clears only verified success", async () => {
    const f = fixture();
    f.request.mockImplementationOnce(async (_path, init) => {
      const saved = f.manager().pending()!;
      expect(init!.body).toBe(JSON.stringify(saved.payload));
      expect(saved.payload.request_id).toBe(requestId);
      return response(saved.payload);
    });
    expect((await f.manager().confirm(draft())).id).toBe(entry);
    expect(f.request).toHaveBeenCalledTimes(1);
    expect(f.manager().pending()).toBeNull();
  });
  it("never dispatches when storage fails or the context changes", async () => {
    const f = fixture();
    f.store.setItem.mockImplementationOnce(() => {
      throw new Error("Quota");
    });
    await expect(f.manager().confirm(draft())).rejects.toMatchObject({
      code: "storage",
    });
    expect(f.request).not.toHaveBeenCalled();
    f.context.mockImplementation(() => {
      throw new SessionError(409, "Session changed");
    });
    await expect(f.manager().confirm(draft())).rejects.toBeInstanceOf(
      SessionError,
    );
    expect(f.request).not.toHaveBeenCalled();
  });
  it("retains unknown results across reload, reconciles using GET and never auto-replays", async () => {
    const f = fixture();
    f.request.mockRejectedValueOnce(new SessionError(504, "Timed out"));
    await expect(f.manager().confirm(draft())).rejects.toBeInstanceOf(
      SessionError,
    );
    const saved = f.manager().pending()!;
    const restored = f.manager();
    expect(restored.pending()).toEqual(saved);
    expect(f.request).toHaveBeenCalledTimes(1);
    await expect(restored.confirm(draft("50"))).rejects.toMatchObject({
      code: "pending",
    });
    expect(f.newId).toHaveBeenCalledTimes(1);
    f.request.mockResolvedValueOnce(response(saved.payload));
    expect((await restored.reconcile())!.id).toBe(entry);
    expect(f.request.mock.calls[1]).toEqual([
      "accounting/journal-requests/" + requestId,
    ]);
    expect(restored.pending()).toBeNull();
  });
  it("keeps a not-found request pending and explicitly resends the identical body and ID", async () => {
    const f = fixture();
    f.request.mockRejectedValueOnce(new TypeError("Network loss"));
    await expect(f.manager().confirm(draft())).rejects.toThrow();
    const body = f.request.mock.calls[0][1]!.body;
    f.request.mockRejectedValueOnce(new SessionError(404, "Not yet found"));
    expect(await f.manager().reconcile()).toBeNull();
    expect(f.manager().pending()).not.toBeNull();
    await f.manager().resend();
    expect(f.request.mock.calls[2][1]!.body).toBe(body);
    expect(f.newId).toHaveBeenCalledTimes(1);
  });
  it("permits correction after an initial definite rejection but preserves a retry's rejection", async () => {
    const f = fixture();
    f.request.mockRejectedValueOnce(new SessionError(422, "Rejected"));
    await expect(f.manager().confirm(draft())).rejects.toThrow();
    expect(f.manager().pending()).toBeNull();
    f.request.mockRejectedValueOnce(new SessionError(502, "Unknown"));
    await expect(f.manager().confirm(draft())).rejects.toThrow();
    f.request.mockRejectedValueOnce(new SessionError(403, "Role revoked"));
    await expect(f.manager().resend()).rejects.toThrow();
    expect(f.manager().pending()).not.toBeNull();
  });
  it("preserves a first conflict and does not let malformed success clear the identity", async () => {
    const f = fixture();
    f.request.mockRejectedValueOnce(new SessionError(409, "Conflict"));
    await expect(f.manager().confirm(draft())).rejects.toThrow();
    const pending = f.manager().pending()!;
    f.request.mockResolvedValueOnce({
      ...response(pending.payload),
      total_credit: "0.00",
    });
    await expect(f.manager().reconcile()).rejects.toMatchObject({
      code: "response",
    });
    expect(f.manager().pending()).toEqual(pending);
  });
  it.each([
    "organization_id",
    "branch_id",
    "request_id",
    "posted_by",
    "currency",
    "description",
    "lines",
  ])("does not accept a mismatched response %s", async (field) => {
    const f = fixture();
    f.request.mockImplementationOnce(async (_path, init) => {
      const result = response(JSON.parse(init!.body as string));
      return { ...result, [field]: field === "lines" ? [] : "foreign" };
    });
    await expect(f.manager().confirm(draft())).rejects.toMatchObject({
      code: "response",
    });
    expect(f.manager().pending()).not.toBeNull();
  });
  it("uses explicit branch lookup and isolates user, organization and branch storage slots", async () => {
    const f = fixture({ ...scope, branchId: branch });
    f.request.mockRejectedValueOnce(new Error("Lost"));
    await expect(
      f.manager().confirm({ ...draft(), branch_id: branch }),
    ).rejects.toThrow();
    expect(readPendingJournal(f.store, scope)).toBeNull();
    expect(
      readPendingJournal(f.store, {
        ...scope,
        userId: revenue,
        branchId: branch,
      }),
    ).toBeNull();
    expect(
      readPendingJournal(f.store, {
        ...scope,
        organizationId: revenue,
        branchId: branch,
      }),
    ).toBeNull();
    f.request.mockResolvedValueOnce(response(f.manager().pending()!.payload));
    await f.manager().reconcile();
    expect(f.request.mock.calls[1][0]).toBe(
      "accounting/journal-requests/" + requestId + "?branch_id=" + branch,
    );
  });
  it("fails closed on corrupt or foreign saved payloads without erasing or sending them", async () => {
    const f = fixture();
    const key = journalStorageKey(scope);
    f.data.set(key, "{corrupt");
    expect(() => f.manager().pending()).toThrow();
    await expect(f.manager().confirm(draft())).rejects.toThrow();
    expect(f.request).not.toHaveBeenCalled();
    expect(f.data.get(key)).toBe("{corrupt");
    f.data.set(
      key,
      JSON.stringify({
        version: 1,
        userId: user,
        organizationId: revenue,
        payload: { ...normalizeJournal(draft()), request_id: requestId },
      }),
    );
    expect(() => f.manager().pending()).toThrow();
  });
  it("serializes overlapping tab commands and blocks a second financial dispatch", async () => {
    const f = fixture();
    let complete!: (value: unknown) => void;
    f.request.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          complete = resolve;
        }),
    );
    const first = f.manager().confirm(draft());
    await expect(f.manager().confirm(draft())).rejects.toMatchObject({
      code: "pending",
    });
    expect(f.request).toHaveBeenCalledTimes(1);
    complete(response(f.manager().pending()!.payload));
    await first;
  });
});
