import { accountingPermissions } from "./accounting";
import { canAccess, type AuthorizationContext } from "./permissions";

export type MerchantAction = {
  id: string;
  href: string;
  title: string;
  description: string;
};

export function merchantHomeActions(context: AuthorizationContext): MerchantAction[] {
  const actions: MerchantAction[] = [];
  if (accountingPermissions.some((code) => canAccess(context, code))) {
    actions.push({
      id: "accounting",
      href: "/accounting",
      title: "المحاسبة",
      description: "دليل الحسابات والقيود حسب صلاحيتك",
    });
  }
  if (
    context.permissions.includes("billing.drafts.read") ||
    context.permissions.includes("billing.drafts.create")
  ) {
    actions.push({
      id: "service-drafts",
      href: "/service-drafts",
      title: "مسودات الخدمات",
      description: "تجهيز مسودات داخلية للعملاء دون إصدار فاتورة ضريبية",
    });
  }
  if (canAccess(context, "branches.read")) {
    actions.push({
      id: "branches",
      href: "/branches",
      title: "الفروع",
      description: "عرض الفروع التي يمكنك الوصول إليها",
    });
  }
  if (canAccess(context, "users.read")) {
    actions.push({
      id: "users",
      href: "/users",
      title: "الفريق",
      description: "عرض موظفي المنشأة وصلاحياتهم",
    });
  }
  if (canAccess(context, "terminals.read")) {
    actions.push({
      id: "devices",
      href: "/devices",
      title: "الأجهزة",
      description: "متابعة الأجهزة المسجلة في المنشأة",
    });
  }
  return actions;
}

const activityNames: Record<string, string> = {
  ORGANIZATION_UPDATED: "تحديث بيانات المنشأة",
  BRANCH_CREATED: "إضافة فرع",
  BRANCH_UPDATED: "تعديل فرع",
  TERMINAL_CREATED: "إضافة جهاز",
  TERMINAL_UPDATED: "تعديل جهاز",
  TERMINAL_REVOKED: "إلغاء جهاز",
  USER_INVITED: "إضافة مستخدم",
  USER_DISABLED: "تعطيل مستخدم",
  ROLE_ASSIGNED: "منح صلاحية",
  ROLE_REMOVED: "إزالة صلاحية",
};

export function merchantActivityLabel(action: string): string {
  return activityNames[action] ?? action.replaceAll("_", " ");
}
