"use server";

import { revalidatePath } from "next/cache";

/**
 * Drop the cached projects list. The page is server-rendered per request, but
 * the client Router Cache keeps its pre-mutation copy of `/`, so navigating
 * back after a create/delete would otherwise show a stale list until a reload.
 */
export async function revalidateProjects(): Promise<void> {
  revalidatePath("/");
}
