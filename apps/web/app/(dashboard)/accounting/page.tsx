import { cookies } from "next/headers";
import { AccountingPage } from "@/components/accounting-workspace";

export default async function Accounting() {
  const english = (await cookies()).get("sm_lang")?.value === "en";
  return <AccountingPage english={english} />;
}
