"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Page } from "@/lib/api";
import {
  accountingAmount,
  accountingListPath,
  canPostAccounting,
  canReadAccounting,
  type Account,
  type Journal,
} from "@/lib/accounting";
import type { AuthorizationContext } from "@/lib/permissions";
import {
  assertContext,
  boundSessionContext,
  SessionError,
} from "@/lib/session";
import {
  JournalCommands,
  JournalProblem,
  journalStorageKey,
  journalTotals,
  normalizeJournal,
  readPendingJournal,
  type JournalDraft,
  type PendingJournal,
} from "@/lib/journal-command";

const ar = {
  title: "إنشاء قيد",
  date: "تاريخ القيد",
  description: "وصف القيد",
  account: "الحساب",
  choose: "اختر حسابًا",
  debit: "مدين",
  credit: "دائن",
  lineDescription: "وصف السطر",
  add: "إضافة سطر",
  remove: "حذف السطر",
  preview: "معاينة القيد",
  review: "مراجعة القيد قبل الترحيل",
  edit: "تعديل",
  confirm: "تأكيد وترحيل القيد",
  acknowledged: "راجعت الحسابات والمبالغ وأوافق على الترحيل.",
  totals: "الإجمالي",
  currency: "المبالغ بالريال السعودي",
  scope: "نطاق القيد",
  organization: "كل المنشأة",
  branch: "الفرع",
  reference: "مرجع العملية",
  invalid:
    "تحقق من التاريخ والوصف والحسابات والمبالغ. لكل سطر طرف واحد موجب، ومجموع المدين يساوي الدائن.",
  storage:
    "تعذر الوصول إلى العملية المحفوظة. أعد تحميل الصفحة أو راجع الدعم قبل تسجيل قيد جديد.",
  uncertain:
    "نتيجة هذه العملية غير مؤكدة. احتفظنا بها على هذا الجهاز؛ تحقق من النتيجة أو أعد إرسال العملية نفسها.",
  check: "التحقق من النتيجة",
  resend: "تأكيد إعادة إرسال العملية نفسها",
  absent:
    "لم يظهر القيد في الخادم حتى الآن. هذا لا يلغي العملية؛ يمكن إعادة إرسالها بنفس المرجع.",
  posted: "تم ترحيل القيد",
  rejected: "رفض الخادم الطلب. راجع البيانات والصلاحيات قبل المحاولة.",
  context: "تغير الحساب أو المنشأة. أعد تحميل الصفحة قبل متابعة العملية.",
  unavailable:
    "تعذر تنفيذ الإجراء. تحقق من الاتصال والصلاحيات ثم أعد المحاولة.",
  loading: "جارٍ تحميل الحسابات…",
  accountError: "تعذر تحميل الحسابات.",
  retry: "إعادة المحاولة",
  previous: "الحسابات السابقة",
  next: "الحسابات التالية",
  accountsRequired: "إنشاء القيد يحتاج صلاحية قراءة الحسابات في هذا النطاق.",
};
type Copy = { [K in keyof typeof ar]: string };
const en: Copy = {
  title: "Create journal",
  date: "Booking date",
  description: "Journal description",
  account: "Account",
  choose: "Choose an account",
  debit: "Debit",
  credit: "Credit",
  lineDescription: "Line description",
  add: "Add line",
  remove: "Remove line",
  preview: "Preview journal",
  review: "Review before posting",
  edit: "Edit",
  confirm: "Confirm and post journal",
  acknowledged: "I reviewed the accounts and amounts and approve posting.",
  totals: "Totals",
  currency: "Amounts in Saudi riyals",
  scope: "Journal scope",
  organization: "Entire organization",
  branch: "Branch",
  reference: "Operation reference",
  invalid:
    "Check date, description, accounts and amounts. Each line needs one positive side; total debits and credits must match.",
  storage:
    "The saved operation is unavailable. Reload or contact support before creating another journal.",
  uncertain:
    "This operation has an uncertain outcome. It remains on this device; check the result or resend the same operation.",
  check: "Check result",
  resend: "Confirm resending the same operation",
  absent:
    "The server has not returned this journal yet. The operation remains pending; it can be resent with the same reference.",
  posted: "Journal posted",
  rejected:
    "The server rejected this request. Review data and permissions before trying again.",
  context:
    "Account or organization changed. Reload before continuing this operation.",
  unavailable:
    "The action could not complete. Check connection and permissions before trying again.",
  loading: "Loading accounts…",
  accountError: "Accounts unavailable.",
  retry: "Retry",
  previous: "Previous accounts",
  next: "Next accounts",
  accountsRequired:
    "Creating a journal requires account read permission in this scope.",
};
const blankLines = (): JournalDraft["lines"] => [
  { account_id: "", debit: "", credit: "", description: null },
  { account_id: "", debit: "", credit: "", description: null },
];
const localDate = () => {
  const date = new Date();
  return (
    String(date.getFullYear()).padStart(4, "0") +
    "-" +
    String(date.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(date.getDate()).padStart(2, "0")
  );
};

export function JournalComposer({
  authorization,
  userId,
  branchId,
  english,
  onPosted,
}: {
  authorization: AuthorizationContext;
  userId: string;
  branchId: string | null;
  english: boolean;
  onPosted: (entry: Journal) => void;
}) {
  const copy = english ? en : ar;
  const scope = useMemo(
    () => ({ userId, organizationId: authorization.organization.id, branchId }),
    [userId, authorization.organization.id, branchId],
  );
  const key = journalStorageKey(scope);
  const canPost = canPostAccounting(authorization, branchId);
  const canRead = canReadAccounting(
    authorization,
    "accounting.accounts.read",
    branchId,
  );
  const canReconcile = canReadAccounting(
    authorization,
    "accounting.journals.read",
    branchId,
  );
  const [lines, setLines] = useState(blankLines);
  const [date, setDate] = useState(localDate);
  const [description, setDescription] = useState("");
  const [preview, setPreview] = useState<JournalDraft | null>(null);
  const [pending, setPending] = useState<PendingJournal | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [ready, setReady] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [accountPage, setAccountPage] = useState(1);
  const [names, setNames] = useState<Record<string, string>>({});
  const inFlight = useRef(false);
  const alive = useRef(false);
  const accounts = useQuery({
    queryKey: [
      "accounting",
      scope.organizationId,
      branchId,
      "accounts",
      accountPage,
    ],
    enabled: canPost && canRead,
    retry: false,
    queryFn: () =>
      api<Page<Account>>(accountingListPath("accounts", branchId, accountPage)),
  });
  useEffect(() => {
    alive.current = true;
    function load(external = false) {
      try {
        boundSessionContext();
        setPending(readPendingJournal(window.localStorage, scope));
        setBlocked(false);
        if (external) {
          setPreview(null);
          setAcknowledged(false);
          setMessage("");
        }
      } catch {
        setPending(null);
        setBlocked(true);
      }
      setReady(true);
    }
    load();
    const changed = (event: StorageEvent) => {
      if (event.key === key || event.key === null) load(true);
    };
    window.addEventListener("storage", changed);
    return () => {
      alive.current = false;
      window.removeEventListener("storage", changed);
    };
  }, [key, scope]);

  function commands() {
    const context = boundSessionContext();
    return new JournalCommands(
      scope,
      window.localStorage,
      api,
      async (name, action) => {
        if (!navigator.locks) throw new JournalProblem("storage");
        return navigator.locks.request(
          name,
          { ifAvailable: true },
          async (lock) => {
            if (!lock) throw new JournalProblem("pending");
            return action();
          },
        );
      },
      () => assertContext(context),
      () => crypto.randomUUID(),
    );
  }
  async function perform(kind: "confirm" | "check" | "resend") {
    if (inFlight.current || blocked || !ready) return;
    if (
      (kind === "confirm" || kind === "resend") &&
      (!acknowledged || !canPost)
    )
      return;
    if (kind === "check" && !canReconcile) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const manager = commands();
      const result =
        kind === "check"
          ? await manager.reconcile()
          : kind === "resend"
            ? await manager.resend()
            : preview
              ? await manager.confirm(preview)
              : null;
      if (!alive.current) return;
      setPending(manager.pending());
      setAcknowledged(false);
      if (result) {
        setPreview(null);
        setDescription("");
        setLines(blankLines());
        setDate(localDate());
        setMessage(copy.posted + " · " + result.id);
        onPosted(result);
      } else setMessage(copy.absent);
    } catch (failure) {
      if (!alive.current) return;
      try {
        setPending(readPendingJournal(window.localStorage, scope));
      } catch {
        setBlocked(true);
      }
      setAcknowledged(false);
      if (failure instanceof JournalProblem && failure.code === "storage")
        setError(copy.storage);
      else if (
        failure instanceof SessionError &&
        failure.status === 409 &&
        failure.message.includes("Session changed")
      ) {
        setBlocked(true);
        setPending(null);
        setPreview(null);
        setError(copy.context);
      } else if (
        failure instanceof SessionError &&
        [400, 403, 404, 413, 422].includes(failure.status)
      )
        setError(copy.rejected);
      else setError(copy.unavailable);
    } finally {
      inFlight.current = false;
      if (alive.current) setBusy(false);
    }
  }
  function makePreview(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      setPreview(
        normalizeJournal({
          branch_id: branchId,
          booking_date: date,
          description,
          lines,
        }),
      );
      setAcknowledged(false);
    } catch {
      setError(copy.invalid);
    }
  }
  function updateLine(
    index: number,
    field: keyof JournalDraft["lines"][number],
    value: string,
  ) {
    setLines((previous) =>
      previous.map((line, i) =>
        i === index ? { ...line, [field]: value } : line,
      ),
    );
    if (field === "account_id") {
      const account = accounts.data?.items.find((row) => row.id === value);
      if (account)
        setNames((previous) => ({
          ...previous,
          [value]: account.code + " — " + account.name,
        }));
    }
  }
  if (!canPost && !pending && !blocked) return null;
  const reviewed = pending?.payload ?? preview;
  const totals = reviewed ? journalTotals(reviewed) : null;
  return (
    <section aria-label={copy.title} className="journal-composer">
      <h2>{copy.title}</h2>
      <p>{copy.currency}</p>
      {blocked && <p role="alert">{copy.storage}</p>}
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      {pending && (
        <p role="status" className="accounting-note">
          {copy.uncertain}
        </p>
      )}
      {reviewed ? (
        <div aria-label={copy.review} role="region">
          <h3>{copy.review}</h3>
          <dl className="accounting-metadata">
            <dt>{copy.date}</dt>
            <dd>{reviewed.booking_date}</dd>
            <dt>{copy.description}</dt>
            <dd>{reviewed.description}</dd>
            <dt>{copy.scope}</dt>
            <dd>
              {branchId === null
                ? copy.organization
                : copy.branch + " " + branchId}
            </dd>
            {pending && (
              <>
                <dt>{copy.reference}</dt>
                <dd dir="ltr">{pending.payload.request_id}</dd>
              </>
            )}
          </dl>
          <div className="accounting-table">
            <table>
              <thead>
                <tr>
                  <th>{copy.account}</th>
                  <th>{copy.lineDescription}</th>
                  <th>{copy.debit}</th>
                  <th>{copy.credit}</th>
                </tr>
              </thead>
              <tbody>
                {reviewed.lines.map((line, i) => (
                  <tr key={i}>
                    <td>{names[line.account_id] ?? line.account_id}</td>
                    <td>{line.description ?? "—"}</td>
                    <td dir="ltr" className="accounting-money">
                      {accountingAmount(line.debit)}
                    </td>
                    <td dir="ltr" className="accounting-money">
                      {accountingAmount(line.credit)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <th colSpan={2}>{copy.totals}</th>
                  <td dir="ltr">{accountingAmount(totals!.debit)}</td>
                  <td dir="ltr">{accountingAmount(totals!.credit)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          {canPost && (
            <label className="journal-acknowledgement">
              <input
                type="checkbox"
                checked={acknowledged}
                disabled={busy || blocked}
                onChange={(event) => setAcknowledged(event.target.checked)}
              />
              {copy.acknowledged}
            </label>
          )}
          <div className="row">
            {pending ? (
              <>
                {canReconcile && (
                  <button
                    type="button"
                    disabled={busy || blocked}
                    onClick={() => void perform("check")}
                  >
                    {copy.check}
                  </button>
                )}
                {canPost && (
                  <button
                    type="button"
                    disabled={busy || blocked || !acknowledged}
                    onClick={() => void perform("resend")}
                  >
                    {copy.resend}
                  </button>
                )}
              </>
            ) : (
              <>
                <button
                  type="button"
                  disabled={busy || blocked || !ready || !acknowledged}
                  onClick={() => void perform("confirm")}
                >
                  {copy.confirm}
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    setPreview(null);
                    setAcknowledged(false);
                  }}
                >
                  {copy.edit}
                </button>
              </>
            )}
          </div>
        </div>
      ) : canPost && canRead ? (
        <form onSubmit={makePreview}>
          <div className="journal-fields">
            <label>
              {copy.date}
              <input
                type="date"
                name="booking_date"
                required
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </label>
            <label>
              {copy.description}
              <input
                name="journal_description"
                required
                maxLength={500}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
          </div>
          {accounts.isPending && <p aria-busy="true">{copy.loading}</p>}
          {accounts.isError && (
            <p role="alert">
              {copy.accountError}{" "}
              <button type="button" onClick={() => void accounts.refetch()}>
                {copy.retry}
              </button>
            </p>
          )}
          <div className="row">
            <button
              type="button"
              disabled={accountPage === 1 || accounts.isFetching}
              onClick={() => setAccountPage((p) => p - 1)}
            >
              {copy.previous}
            </button>
            <button
              type="button"
              disabled={
                !accounts.data ||
                accounts.data.items.length < 20 ||
                accounts.isFetching
              }
              onClick={() => setAccountPage((p) => p + 1)}
            >
              {copy.next}
            </button>
          </div>
          <fieldset disabled={busy || blocked || !ready}>
            {lines.map((line, i) => (
              <div className="journal-line" key={i}>
                <label>
                  {copy.account + " " + (i + 1)}
                  <select
                    required
                    name={"account_" + i}
                    value={line.account_id}
                    onChange={(e) =>
                      updateLine(i, "account_id", e.target.value)
                    }
                  >
                    <option value="">{copy.choose}</option>
                    {line.account_id &&
                      !accounts.data?.items.some(
                        (a) => a.id === line.account_id && a.is_active,
                      ) && (
                        <option value={line.account_id}>
                          {names[line.account_id] ?? line.account_id}
                        </option>
                      )}
                    {accounts.data?.items
                      .filter((a) => a.is_active)
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.code + " — " + a.name}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  {copy.debit + " " + (i + 1)}
                  <input
                    inputMode="decimal"
                    dir="ltr"
                    name={"debit_" + i}
                    value={line.debit}
                    onChange={(e) => updateLine(i, "debit", e.target.value)}
                    placeholder="0.00"
                  />
                </label>
                <label>
                  {copy.credit + " " + (i + 1)}
                  <input
                    inputMode="decimal"
                    dir="ltr"
                    name={"credit_" + i}
                    value={line.credit}
                    onChange={(e) => updateLine(i, "credit", e.target.value)}
                    placeholder="0.00"
                  />
                </label>
                <label>
                  {copy.lineDescription + " " + (i + 1)}
                  <input
                    maxLength={500}
                    name={"line_description_" + i}
                    value={line.description ?? ""}
                    onChange={(e) =>
                      updateLine(i, "description", e.target.value)
                    }
                  />
                </label>
                <button
                  type="button"
                  disabled={lines.length <= 2}
                  aria-label={copy.remove + " " + (i + 1)}
                  onClick={() =>
                    setLines((rows) => rows.filter((_, index) => index !== i))
                  }
                >
                  {copy.remove}
                </button>
              </div>
            ))}
            <div className="row">
              <button
                type="button"
                disabled={lines.length >= 100}
                onClick={() => setLines((rows) => [...rows, blankLines()[0]])}
              >
                {copy.add}
              </button>
              <button
                type="submit"
                disabled={accounts.isError || !accounts.data}
              >
                {copy.preview}
              </button>
            </div>
          </fieldset>
        </form>
      ) : canPost ? (
        <p>{copy.accountsRequired}</p>
      ) : null}
    </section>
  );
}
