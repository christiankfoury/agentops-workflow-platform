"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { seedDemoDataset } from "@/lib/api";
import type { DemoSeedTarget } from "@/lib/types";

const demoTargets = new Set<DemoSeedTarget>([
  "sales-report",
  "customer-feedback",
  "incident-log",
  "full-evaluation",
]);

const demoDestinations: Record<DemoSeedTarget, string> = {
  "sales-report": "/workflow-comparison?search=Sales",
  "customer-feedback": "/workflow-comparison?search=Feedback",
  "incident-log": "/workflow-comparison?search=Incident",
  "full-evaluation": "/evaluation",
};

export async function seedDemoAction(formData: FormData): Promise<void> {
  const target = formData.get("target");
  if (typeof target !== "string" || !demoTargets.has(target as DemoSeedTarget)) {
    throw new Error("Invalid demo target.");
  }

  await seedDemoDataset(target as DemoSeedTarget);
  revalidatePath("/");
  revalidatePath("/demo");
  revalidatePath("/workflow-runs");
  revalidatePath("/evaluation");
  revalidatePath("/workflow-comparison");
  revalidatePath("/agent-performance");
  revalidatePath("/improvements");

  redirect(demoDestinations[target as DemoSeedTarget]);
}
