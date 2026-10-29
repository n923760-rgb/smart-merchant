"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, type Branch, type Page } from "@/lib/api";
import { canAccess, canManage, type AuthorizationContext } from "@/lib/permissions";
import { merchantActivityLabel, merchantHomeActions } from "@/lib/merchant-home";

type Activity = {
  id: string;
  action: string;
  entity_type: string;
  created_at: string;
};

export default function Overview() {
  const context = useQuery({
    queryKey: ["merchant-home", "context"],
    queryFn: () => api<AuthorizationContext>("auth/context"),
    refetchOnMount: "always",
    retry: false,
  });
  const organizationId = context.data?.organization.id;
  const mayReadBranches = !!context.data && canAccess(context.data, "branches.read");
  // The audit API requires an organization-level grant; branch access alone is not enough.
  const mayReadAudit = !!context.data && canManage(context.data, "audit.read");
  const branches = useQuery({
    queryKey: ["merchant-home", organizationId, "branches"],
    enabled: !!organizationId && mayReadBranches,
    queryFn: () => api<Page<Branch>>("branches?page=1&page_size=5"),
    retry: false,
  });
  const activity = useQuery({
    queryKey: ["merchant-home", organizationId, "audit"],
    enabled: !!organizationId && mayReadAudit,
    queryFn: () => api<Page<Activity>>("audit?page=1&page_size=5"),
    retry: false,
  });

  if (context.isPending) {
    return <section className="merchant-home" role="status">جارٍ تحميل بيانات المنشأة…</section>;
  }
  if (context.isError || !context.data) {
    return (
      <section className="merchant-home">
        <h1>نظرة عامة</h1>
        <p role="alert">تعذّر تحميل بيانات المنشأة. لا نعرض بيانات تقديرية بدلها.</p>
        <button type="button" onClick={() => void context.refetch()}>إعادة المحاولة</button>
      </section>
    );
  }

  const actions = merchantHomeActions(context.data);
  return (
    <div className="merchant-home">
      <section className="merchant-home-intro">
        <p className="merchant-home-eyebrow">مركز إدارة أعمالك</p>
        <h1>{context.data.organization.name}</h1>
        <p>
          هذه الصفحة تعرض المعلومات المتاحة والمصرح بها من النظام الحالي.
          مؤشرات المبيعات والطلبات عبر القنوات ستظهر بعد ربط مصادر موثوقة واختبارها.
        </p>
        <div className="merchant-home-indicators">
          <span>المنشأة: {context.data.organization.name}</span>
          <span>مصادر البيع الخارجية: لم تُفعّل بعد</span>
        </div>
      </section>

      <section aria-labelledby="merchant-home-actions">
        <h2 id="merchant-home-actions">ماذا تريد أن تنجز؟</h2>
        {actions.length === 0 ? (
          <p>لا توجد وحدات تشغيل مصرح بها لهذا الحساب حاليًا.</p>
        ) : (
          <div className="merchant-home-grid">
            {actions.map((action) => (
              <Link className="merchant-home-action" href={action.href} key={action.id}>
                <strong>{action.title}</strong>
                <span>{action.description}</span>
                <span aria-hidden="true">←</span>
              </Link>
            ))}
          </div>
        )}
      </section>

      <div className="merchant-home-columns">
        {mayReadBranches && (
          <section aria-labelledby="merchant-home-branches">
            <div className="merchant-home-heading">
              <h2 id="merchant-home-branches">الفروع الظاهرة</h2>
              <Link href="/branches">كل الفروع</Link>
            </div>
            {branches.isPending && <p role="status">جارٍ تحميل الفروع…</p>}
            {branches.isError && (
              <p role="alert">
                تعذّر تحميل الفروع.{" "}
                <button type="button" onClick={() => void branches.refetch()}>إعادة المحاولة</button>
              </p>
            )}
            {branches.data && (
              branches.data.items.length === 0
                ? <p>لا توجد فروع ظاهرة في نطاق صلاحياتك.</p>
                : <ul className="merchant-home-list">
                    {branches.data.items.map((branch) => (
                      <li key={branch.id}>
                        <span>{branch.name} <small>{branch.code}</small></span>
                        <span>{branch.status === "ACTIVE" ? "نشط" : "غير نشط"}</span>
                      </li>
                    ))}
                  </ul>
            )}
            <p className="merchant-home-footnote">أول خمسة فروع مصرح بها فقط، وليست إحصاءً لكل فروع المنشأة.</p>
          </section>
        )}

        {mayReadAudit && (
          <section aria-labelledby="merchant-home-activity">
            <h2 id="merchant-home-activity">آخر أنشطة الإدارة</h2>
            {activity.isPending && <p role="status">جارٍ تحميل النشاط…</p>}
            {activity.isError && (
              <p role="alert">
                تعذّر تحميل سجل النشاط.{" "}
                <button type="button" onClick={() => void activity.refetch()}>إعادة المحاولة</button>
              </p>
            )}
            {activity.data && (
              activity.data.items.length === 0
                ? <p>لا توجد أحداث إدارية مسجلة حتى الآن.</p>
                : <ul className="merchant-home-list">
                    {activity.data.items.map((item) => (
                      <li key={item.id}>
                        <span>{merchantActivityLabel(item.action)}</span>
                        <time dateTime={item.created_at}>
                          {new Date(item.created_at).toLocaleString("ar-SA")}
                        </time>
                      </li>
                    ))}
                  </ul>
            )}
            <p className="merchant-home-footnote">سجل الإدارة فقط، وليس سجل المبيعات والطلبات. الأوقات وفق جهازك.</p>
          </section>
        )}
      </div>

      <section className="merchant-home-notice" aria-labelledby="merchant-home-future">
        <h2 id="merchant-home-future">التجارة الإلكترونية والفعلية في لوحة واحدة</h2>
        <p>
          نجهّز ربط قنوات البيع وإظهار الطلبات والمخزون والمبيعات في مكان واحد.
          هذه الوظائف ليست نشطة بعد، ولن نعرض أرقامًا غير متصلة ببيانات موثوقة.
        </p>
      </section>
    </div>
  );
}
