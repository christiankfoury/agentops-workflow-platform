"use server";

import { revalidatePath } from "next/cache";
import { updateMembership } from "@/lib/api";

export async function saveMember(
  _previous: { error?: string; success?: string }, form: FormData,
): Promise<{ error?: string; success?: string }> {
  const userId = String(form.get("user_id") ?? "");
  const role = String(form.get("role") ?? "");
  if (!/^[0-9a-f-]{36}$/i.test(userId) || !["viewer", "operator", "reviewer", "admin"].includes(role)) {
    return { error: "Choose a provisioned user and a valid role." };
  }
  try {
    await updateMembership(userId, role, form.get("active") === "on");
  } catch {
    return { error: "The membership was not changed. Check your administrator access, the user ID, and that another active administrator remains." };
  }
  revalidatePath("/account/members");
  return { success: "Membership saved." };
}
