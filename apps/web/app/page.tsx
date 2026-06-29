"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/lib/auth";

export default function Home() {
  const { ready, authed } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!ready) return;
    router.replace(authed ? "/orgs" : "/login");
  }, [ready, authed, router]);
  return <div className="p-8 text-slate-500">Loading…</div>;
}
