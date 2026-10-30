"use client";

import { useRef, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Page } from "@/lib/api";
import { type AuthorizationContext } from "@/lib/permissions";
import {
  draftLineCents,
  draftTotalCents,
  formatDraftCents,
  validServiceDraftLines,
  type DraftInputLine,
  type ServiceDraft,
} from "@/lib/service-drafts";

type DraftSubmission = {
  request_id: string;
  customer_name: string;
  customer_email: string | null;
  lines: { service_name: string; quantity: string; unit_price: string }[];
};

function makeLine(): DraftInputLine {
  return { id: crypto.randomUUID(), service_name: "", quantity: "1.000", unit_price: "0.00" };
}

export function ServiceDraftWorkspace() {
  const [customerName, setCustomerName] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [lines, setLines] = useState<DraftInputLine[]>([
    { id: "first", service_name: "", quantity: "1.000", unit_price: "0.00" },
  ]);
  const [pending, setPending] = useState<DraftSubmission | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<ServiceDraft | null>(null);
  const [selected, setSelected] = useState<ServiceDraft | null>(null);
  // The request identity is captured synchronously, before React can repaint
  // or a rapid second tap can generate another request for the same draft.
  const operationRef = useRef<DraftSubmission | null>(null);
  const inFlightRef = useRef(false);

  const context = useQuery({
    queryKey: ["service-drafts", "context"],
    queryFn: () => api<AuthorizationContext>("auth/context"),
    retry: false,
  });
  const orgId = context.data?.organization.id;
  const canRead = !!context.data?.permissions.includes("billing.drafts.read");
  const canCreate = !!context.data?.permissions.includes("billing.drafts.create");
  const drafts = useQuery({
    queryKey: ["service-drafts", orgId, "list"],
    enabled: !!orgId && canRead,
    queryFn: () => api<Page<ServiceDraft>>("billing/service-drafts?page=1&page_size=20"),
    retry: false,
  });

  const preview = draftTotalCents(lines);

  function replaceLine(id: string, field: "service_name" | "quantity" | "unit_price", value: string) {
    setLines((old) => old.map((line) =>
      line.id === id ? { ...line, [field]: value } : line,
    ));
  }

  function reset() {
    operationRef.current = null;
    inFlightRef.current = false;
    setSaved(null);
    setSelected(null);
    setPending(null);
    setSaving(false);
    setError("");
    setCustomerName("");
    setCustomerEmail("");
    setLines([makeLine()]);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlightRef.current || saving || !canCreate || saved) return;
    let submission = operationRef.current ?? pending;
    if (!submission) {
      if (!customerName.trim() || !validServiceDraftLines(lines) || preview === null) {
        setError("أكمل اسم العميل، والخدمات، والكميات والأسعار بصيغة صحيحة.");
        return;
      }
      submission = {
        request_id: crypto.randomUUID(),
        customer_name: customerName.trim(),
        customer_email: customerEmail.trim() || null,
        lines: lines.map((line) => ({
          service_name: line.service_name.trim(),
          quantity: line.quantity,
          unit_price: line.unit_price,
        })),
      };
      operationRef.current = submission;
      setPending(submission);
    }
    inFlightRef.current = true;
    setSaving(true);
    setError("");
    try {
      const result = await api<ServiceDraft>("billing/service-drafts", {
        method: "POST",
        body: JSON.stringify(submission),
      });
      if (result.status !== "DRAFT" || result.tax_status !== "NOT_EVALUATED") {
        throw new Error("تعذّر تأكيد حالة المسودة المحفوظة.");
      }
      setSaved(result);
      setSelected(result);
      operationRef.current = null;
      setPending(null);
      await drafts.refetch();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "تعذّر تأكيد الحفظ.");
      // Retain identical request ID and body. On ambiguous network outcomes,
      // retry the exact command rather than risk creating a duplicate draft.
    } finally {
      inFlightRef.current = false;
      setSaving(false);
    }
  }

  if (context.isPending) return <section role="status">جارٍ التحقق من صلاحيات الفواتير…</section>;
  if (!context.data || context.isError) {
    return <section role="alert">تعذّر التحقق من المنشأة والصلاحيات. أعد تحميل الصفحة.</section>;
  }
  if (!canCreate && !canRead) return <section role="alert">ليس لديك صلاحية الوصول إلى مسودات الخدمات.</section>;

  return (
    <div className="service-drafts">
      <section className="service-drafts-intro">
        <h1>مسودات الخدمات</h1>
        <p>جهّز تفاصيل الخدمة والعميل واحفظ نسخة داخلية للمتابعة. لا تحتاج إلى جهاز كاشير أو مخزون.</p>
        <p className="service-drafts-warning" role="note">
          مسودة داخلية فقط — لم تُحسب الضريبة، وليست فاتورة ضريبية مُصدرة.
        </p>
      </section>

      {canCreate && (
        <section aria-labelledby="draft-create-heading">
          <div className="service-drafts-heading">
            <h2 id="draft-create-heading">إنشاء مسودة</h2>
            {saved && <button type="button" onClick={reset}>مسودة جديدة</button>}
          </div>
          {saved ? (
            <div role="status" className="service-drafts-success">
              <strong>تم حفظ المسودة.</strong>
              <p>إجمالي الخدمات قبل الضريبة: {saved.amount_before_tax} ريال. لم يتم إصدار فاتورة ضريبية أو ترحيل قيد محاسبي.</p>
            </div>
          ) : (
            <form onSubmit={(event) => void submit(event)} className="service-drafts-form">
              <div className="service-drafts-customer">
                <label>
                  اسم العميل
                  <input required maxLength={180} value={customerName}
                    disabled={!!pending || saving}
                    onChange={(event) => setCustomerName(event.target.value)}
                    placeholder="اسم العميل أو المنشأة" />
                </label>
                <label>
                  البريد الإلكتروني (اختياري)
                  <input type="email" value={customerEmail}
                    disabled={!!pending || saving}
                    onChange={(event) => setCustomerEmail(event.target.value)}
                    placeholder="example@domain.com" />
                </label>
              </div>
              <fieldset disabled={!!pending || saving}>
                <legend>الخدمات</legend>
                {lines.map((line, index) => (
                  <div className="service-drafts-line" key={line.id}>
                    <label>
                      الخدمة {index + 1}
                      <input required maxLength={180} value={line.service_name}
                        onChange={(event) => replaceLine(line.id, "service_name", event.target.value)}
                        placeholder="وصف الخدمة" />
                    </label>
                    <label>
                      الكمية
                      <input required inputMode="decimal" value={line.quantity}
                        onChange={(event) => replaceLine(line.id, "quantity", event.target.value)} />
                    </label>
                    <label>
                      سعر الوحدة (ر.س)
                      <input required inputMode="decimal" value={line.unit_price}
                        onChange={(event) => replaceLine(line.id, "unit_price", event.target.value)} />
                    </label>
                    <div className="service-drafts-line-total">
                      <small>الإجمالي</small>
                      <strong>{formatDraftCents(draftLineCents(line.quantity, line.unit_price))}</strong>
                    </div>
                    {lines.length > 1 && (
                      <button type="button" className="service-drafts-secondary"
                        onClick={() => setLines((old) => old.filter((row) => row.id !== line.id))}>
                        حذف
                      </button>
                    )}
                  </div>
                ))}
                {lines.length < 100 && (
                  <button type="button" className="service-drafts-secondary"
                    onClick={() => setLines((old) => [...old, makeLine()])}>إضافة خدمة</button>
                )}
              </fieldset>
              <div className="service-drafts-summary">
                <span>المجموع قبل الضريبة</span>
                <strong>{formatDraftCents(preview)} ر.س</strong>
              </div>
              {error && (
                <p role="alert">
                  {error} {pending && "لم نتأكد من نتيجة العملية؛ أعد المحاولة بنفس رقم الطلب."}
                </p>
              )}
              <button type="submit" disabled={saving}>
                {saving ? "جارٍ التحقق من الحفظ…" : pending ? "إعادة التحقق من الحفظ" : "حفظ مسودة داخلية"}
              </button>
            </form>
          )}
        </section>
      )}

      {canRead && (
        <section aria-labelledby="service-draft-list">
          <div className="service-drafts-heading">
            <h2 id="service-draft-list">آخر المسودات</h2>
            <button type="button" className="service-drafts-secondary"
              onClick={() => void drafts.refetch()} disabled={drafts.isFetching}>تحديث</button>
          </div>
          {drafts.isPending && <p role="status">جارٍ تحميل المسودات…</p>}
          {drafts.isError && <p role="alert">تعذّر تحميل المسودات. أعد المحاولة.</p>}
          {drafts.data?.items.length === 0 && <p>لا توجد مسودات محفوظة حتى الآن.</p>}
          {drafts.data?.items.map((draft) => (
            <button key={draft.id} type="button" className="service-drafts-list-item"
              onClick={() => setSelected(draft)}>
              <strong>{draft.customer_name}</strong>
              <span>{draft.amount_before_tax} ر.س · مسودة داخلية</span>
            </button>
          ))}
          <p className="service-drafts-footnote">يُعرض آخر 20 مستندًا فقط. جميع المبالغ قبل احتساب الضريبة.</p>
          {selected && (
            <div className="service-drafts-detail">
              <h3>تفاصيل المسودة — {selected.customer_name}</h3>
              <ul>
                {selected.lines.map((line) => (
                  <li key={line.line_number}>{line.service_name}: {line.quantity} × {line.unit_price} = {line.line_total} ر.س</li>
                ))}
              </ul>
              <p><strong>المجموع قبل الضريبة: {selected.amount_before_tax} ر.س</strong></p>
              <p>الحالة: مسودة داخلية — الضريبة غير محسوبة.</p>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
