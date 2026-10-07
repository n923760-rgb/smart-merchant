"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Page, type Me } from "@/lib/api";
import { JournalComposer } from "./journal-composer";
import type { AuthorizationContext } from "@/lib/permissions";
import {
  accountingAmount,
  accountingListPath,
  accountingScopes,
  canReadAccounting,
  type Account,
  type Journal,
} from "@/lib/accounting";

const ar = {
  title: "المحاسبة",
  intro: "دليل الحسابات والقيود المرحلة — دون الحاجة إلى كاشير أو وردية.",
  workflow:
    "أنشئ قيدًا بعد المعاينة والتأكيد بحسب صلاحياتك. عكس القيود والفترات والتقارير مراحل تالية.",
  scope: "نطاق العرض",
  organization: "كل المنشأة",
  branch: "فرع",
  accounts: "دليل الحسابات",
  journals: "القيود المرحلة",
  details: "تفاصيل القيد",
  code: "الرمز",
  name: "اسم الحساب",
  type: "النوع",
  state: "الحالة",
  active: "نشط",
  inactive: "غير نشط",
  date: "تاريخ القيد",
  description: "الوصف",
  debit: "المدين",
  credit: "الدائن",
  currency: "العملة",
  view: "عرض التفاصيل",
  close: "إغلاق التفاصيل",
  previous: "السابق",
  next: "التالي",
  page: "صفحة",
  empty: "لا توجد سجلات في هذا النطاق.",
  loading: "جارٍ التحميل…",
  retry: "إعادة المحاولة",
  failure: "تعذّر تحميل السجلات. لم يتم عرض نتيجة فارغة بدل الخطأ.",
  denied: "لا تملك صلاحية قراءة هذه السجلات في النطاق المحدد.",
  noAccess: "لا تملك صلاحية قراءة المحاسبة.",
  account: "الحساب",
  totals: "إجمالي القيد",
  id: "معرّف القيد",
  reversal: "قيد عكسي للأصل",
  postedAt: "وقت الترحيل",
};
type Copy = { [K in keyof typeof ar]: string };
const en: Copy = {
  title: "Accounting",
  intro:
    "Chart accounts and posted journals — no POS terminal or shift required.",
  workflow:
    "Authorized users can preview and confirm a journal. Reversal controls, periods and reports follow separately.",
  scope: "Viewing scope",
  organization: "Entire organization",
  branch: "Branch",
  accounts: "Chart accounts",
  journals: "Posted journals",
  details: "Journal details",
  code: "Code",
  name: "Account name",
  type: "Type",
  state: "Status",
  active: "Active",
  inactive: "Inactive",
  date: "Booking date",
  description: "Description",
  debit: "Debit",
  credit: "Credit",
  currency: "Currency",
  view: "View details",
  close: "Close details",
  previous: "Previous",
  next: "Next",
  page: "Page",
  empty: "No records in this scope.",
  loading: "Loading…",
  retry: "Retry",
  failure:
    "Records could not be loaded. This is an error, not an empty result.",
  denied: "You cannot read these records in the selected scope.",
  noAccess: "No accounting read permission.",
  account: "Account",
  totals: "Journal totals",
  id: "Journal ID",
  reversal: "Reversal of original",
  postedAt: "Posted at",
};
const types = {
  ASSET: "أصول",
  LIABILITY: "التزامات",
  EQUITY: "حقوق ملكية",
  REVENUE: "إيرادات",
  EXPENSE: "مصروفات",
};

function ReadError({ copy, retry }: { copy: Copy; retry: () => void }) {
  return (
    <p role="alert">
      {copy.failure}{" "}
      <button type="button" onClick={retry}>
        {copy.retry}
      </button>
    </p>
  );
}
function Pagination({
  copy,
  page,
  busy,
  size,
  change,
}: {
  copy: Copy;
  page: number;
  busy: boolean;
  size: number;
  change: (page: number) => void;
}) {
  return (
    <div className="accounting-pagination">
      <button
        type="button"
        disabled={busy || page === 1}
        onClick={() => change(page - 1)}
      >
        {copy.previous}
      </button>
      <span>
        {copy.page} {page}
      </span>
      <button
        type="button"
        disabled={busy || size < 20}
        onClick={() => change(page + 1)}
      >
        {copy.next}
      </button>
    </div>
  );
}

export function AccountingPage({ english }: { english: boolean }) {
  const authorization = useQuery({
    queryKey: ["accounting-authorization"],
    queryFn: () => api<AuthorizationContext>("auth/context"),
    retry: false,
  });
  const user = useQuery({
    queryKey: ["me"],
    queryFn: () => api<Me>("auth/me"),
    retry: false,
  });
  if (authorization.isError || user.isError)
    return (
      <section role="alert">
        {english
          ? "Accounting permissions unavailable."
          : "تعذّر تحميل صلاحيات المحاسبة."}{" "}
        <button
          onClick={() => {
            void authorization.refetch();
            void user.refetch();
          }}
        >
          {english ? en.retry : ar.retry}
        </button>
      </section>
    );
  if (!authorization.data || !user.data)
    return (
      <section aria-busy="true">{english ? en.loading : ar.loading}</section>
    );
  return (
    <AccountingWorkspace
      key={user.data.id + ":" + authorization.data.organization.id}
      authorization={authorization.data}
      userId={user.data.id}
      english={english}
    />
  );
}

function AccountingWorkspace({
  userId,
  authorization,
  english,
}: {
  authorization: AuthorizationContext;
  userId: string;
  english: boolean;
}) {
  const scopes = accountingScopes(authorization);
  const [requestedScope, setScope] = useState(scopes[0]?.id ?? "");
  const copy = english ? en : ar;
  const scope =
    scopes.find((candidate) => candidate.id === requestedScope) ?? scopes[0];
  return (
    <div className="accounting-workspace">
      <section>
        <h1>{copy.title}</h1>
        <p>{copy.intro}</p>
        <p className="accounting-note">{copy.workflow}</p>
        {!scope ? (
          <p role="alert">{copy.noAccess}</p>
        ) : (
          <label className="accounting-scope">
            {copy.scope}
            <select
              aria-label={copy.scope}
              value={scope.id}
              onChange={(event) => setScope(event.target.value)}
            >
              {scopes.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.branchId === null
                    ? copy.organization
                    : `${copy.branch} ${option.branchId}`}
                </option>
              ))}
            </select>
          </label>
        )}
      </section>
      {scope && (
        <AccountingRecords
          key={`${authorization.organization.id}:${scope.id}`}
          authorization={authorization}
          userId={userId}
          branchId={scope.branchId}
          copy={copy}
          english={english}
        />
      )}
    </div>
  );
}

function AccountingRecords({
  userId,
  authorization,
  branchId,
  copy,
  english,
}: {
  authorization: AuthorizationContext;
  userId: string;
  branchId: string | null;
  copy: Copy;
  english: boolean;
}) {
  const queryClient = useQueryClient();
  const [accountPage, setAccountPage] = useState(1);
  const [journalPage, setJournalPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const readAccounts = canReadAccounting(
    authorization,
    "accounting.accounts.read",
    branchId,
  );
  const readJournals = canReadAccounting(
    authorization,
    "accounting.journals.read",
    branchId,
  );
  const org = authorization.organization.id;
  const accounts = useQuery({
    queryKey: ["accounting", org, branchId, "accounts", accountPage],
    enabled: readAccounts,
    retry: false,
    queryFn: () =>
      api<Page<Account>>(accountingListPath("accounts", branchId, accountPage)),
  });
  const journals = useQuery({
    queryKey: ["accounting", org, branchId, "journals", journalPage],
    enabled: readJournals,
    retry: false,
    queryFn: () =>
      api<Page<Journal>>(accountingListPath("journals", branchId, journalPage)),
  });
  const detail = useQuery({
    queryKey: ["accounting", org, branchId, "detail", selected],
    enabled: readJournals && selected !== null,
    retry: false,
    queryFn: () =>
      api<Journal>(`accounting/journals/${encodeURIComponent(selected!)}`),
  });
  return (
    <>
      <JournalComposer
        authorization={authorization}
        userId={userId}
        branchId={branchId}
        english={english}
        onPosted={(entry) => {
          if (readJournals) setSelected(entry.id);
          void queryClient.invalidateQueries({
            queryKey: ["accounting", org, branchId, "journals"],
          });
        }}
      />
      <section aria-label={copy.accounts}>
        <h2>{copy.accounts}</h2>
        {!readAccounts ? (
          <p>{copy.denied}</p>
        ) : (
          <>
            {accounts.isPending && <p aria-busy="true">{copy.loading}</p>}
            {accounts.isError ? (
              <ReadError copy={copy} retry={() => void accounts.refetch()} />
            ) : (
              accounts.data && (
                <>
                  {accounts.data.items.length === 0 ? (
                    <p>{copy.empty}</p>
                  ) : (
                    <div className="accounting-table">
                      <table>
                        <thead>
                          <tr>
                            <th>{copy.code}</th>
                            <th>{copy.name}</th>
                            <th>{copy.type}</th>
                            <th>{copy.state}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {accounts.data.items.map((account) => (
                            <tr key={account.id}>
                              <td dir="ltr">{account.code}</td>
                              <td>{account.name}</td>
                              <td>
                                {english
                                  ? account.account_type
                                  : types[account.account_type]}
                              </td>
                              <td>
                                {account.is_active
                                  ? copy.active
                                  : copy.inactive}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <Pagination
                    copy={copy}
                    page={accountPage}
                    busy={accounts.isFetching}
                    size={accounts.data.items.length}
                    change={setAccountPage}
                  />
                </>
              )
            )}
          </>
        )}
      </section>
      <section aria-label={copy.journals}>
        <h2>{copy.journals}</h2>
        {!readJournals ? (
          <p>{copy.denied}</p>
        ) : (
          <>
            {journals.isPending && <p aria-busy="true">{copy.loading}</p>}
            {journals.isError ? (
              <ReadError copy={copy} retry={() => void journals.refetch()} />
            ) : (
              journals.data && (
                <>
                  {journals.data.items.length === 0 ? (
                    <p>{copy.empty}</p>
                  ) : (
                    <div className="accounting-table">
                      <table>
                        <thead>
                          <tr>
                            <th>{copy.date}</th>
                            <th>{copy.description}</th>
                            <th>{copy.debit}</th>
                            <th>{copy.credit}</th>
                            <th>{copy.currency}</th>
                            <th>{copy.details}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {journals.data.items.map((journal) => (
                            <tr key={journal.id}>
                              <td dir="ltr">{journal.booking_date}</td>
                              <td>{journal.description}</td>
                              <td className="accounting-money" dir="ltr">
                                {accountingAmount(journal.total_debit)}
                              </td>
                              <td className="accounting-money" dir="ltr">
                                {accountingAmount(journal.total_credit)}
                              </td>
                              <td>{journal.currency}</td>
                              <td>
                                <button
                                  type="button"
                                  aria-expanded={selected === journal.id}
                                  onClick={() => setSelected(journal.id)}
                                >
                                  {copy.view}
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <Pagination
                    copy={copy}
                    page={journalPage}
                    busy={journals.isFetching}
                    size={journals.data.items.length}
                    change={setJournalPage}
                  />
                </>
              )
            )}
          </>
        )}
      </section>
      {readJournals && selected !== null && (
        <section aria-label={copy.details}>
          <div className="accounting-heading">
            <h2>{copy.details}</h2>
            <button type="button" onClick={() => setSelected(null)}>
              {copy.close}
            </button>
          </div>
          {detail.isPending && <p aria-busy="true">{copy.loading}</p>}
          {detail.isError ? (
            <ReadError copy={copy} retry={() => void detail.refetch()} />
          ) : (
            detail.data && (
              <>
                <p>{detail.data.description}</p>
                <dl className="accounting-metadata">
                  <dt>{copy.id}</dt>
                  <dd dir="ltr">{detail.data.id}</dd>
                  <dt>{copy.date}</dt>
                  <dd dir="ltr">{detail.data.booking_date}</dd>
                  <dt>{copy.postedAt}</dt>
                  <dd dir="ltr">{detail.data.posted_at}</dd>
                  {detail.data.branch_id && (
                    <>
                      <dt>{copy.branch}</dt>
                      <dd dir="ltr">{detail.data.branch_id}</dd>
                    </>
                  )}
                  {detail.data.reversal_of_id && (
                    <>
                      <dt>{copy.reversal}</dt>
                      <dd dir="ltr">{detail.data.reversal_of_id}</dd>
                    </>
                  )}
                </dl>
                <div className="accounting-table">
                  <table>
                    <thead>
                      <tr>
                        <th>{copy.account}</th>
                        <th>{copy.description}</th>
                        <th>{copy.debit}</th>
                        <th>{copy.credit}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.data.lines.map((line) => {
                        const account = readAccounts
                          ? accounts.data?.items.find(
                              (row) => row.id === line.account_id,
                            )
                          : undefined;
                        return (
                          <tr key={line.line_number}>
                            <td>
                              {account
                                ? `${account.code} — ${account.name}`
                                : line.account_id}
                            </td>
                            <td>{line.description ?? "—"}</td>
                            <td className="accounting-money" dir="ltr">
                              {accountingAmount(line.debit)}
                            </td>
                            <td className="accounting-money" dir="ltr">
                              {accountingAmount(line.credit)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot>
                      <tr>
                        <th colSpan={2}>
                          {copy.totals} ({detail.data.currency})
                        </th>
                        <td className="accounting-money" dir="ltr">
                          {accountingAmount(detail.data.total_debit)}
                        </td>
                        <td className="accounting-money" dir="ltr">
                          {accountingAmount(detail.data.total_credit)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </>
            )
          )}
        </section>
      )}
    </>
  );
}
