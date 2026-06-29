"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { NavLink } from "@/components/ui";
import { apiGet } from "@/lib/api";
import { useAuth, useRequireAuth } from "@/lib/auth";
import type { Org } from "@/lib/types";

export default function OrgLayout({ children }: { children: React.ReactNode }) {
  const ok = useRequireAuth();
  const { orgId } = useParams<{ orgId: string }>();
  const { logout } = useAuth();
  const router = useRouter();
  const [org, setOrg] = useState<Org | null>(null);

  useEffect(() => {
    if (ok) apiGet<Org>(`/orgs/${orgId}`).then(setOrg).catch(() => router.replace("/orgs"));
  }, [ok, orgId, router]);

  if (!ok) return <div className="p-8 text-slate-500">Loading…</div>;

  const base = `/orgs/${orgId}`;
  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-r border-slate-200 bg-white p-4">
        <Link href="/orgs" className="text-xs font-semibold uppercase text-slate-400">
          ← All orgs
        </Link>
        <div className="mb-4 mt-2 truncate text-lg font-bold">{org?.name ?? "…"}</div>
        <nav className="space-y-1">
          <NavLink href={`${base}/links`}>Links</NavLink>
          <NavLink href={`${base}/branches`}>Branches</NavLink>
          <NavLink href={`${base}/media`}>Media</NavLink>
          <NavLink href={`${base}/members`}>Members</NavLink>
          <NavLink href={`${base}/settings`}>Settings</NavLink>
        </nav>
        <button
          onClick={() => { logout(); router.replace("/login"); }}
          className="mt-6 w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-500 hover:bg-slate-100"
        >
          Sign out
        </button>
      </aside>
      <main className="flex-1 px-8 py-8">{children}</main>
    </div>
  );
}
