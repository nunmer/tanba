"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button, Card, ErrorText, Field, Input, PageHeader } from "@/components/ui";
import { apiGet, apiPost } from "@/lib/api";
import { useAuth, useRequireAuth } from "@/lib/auth";
import type { Org } from "@/lib/types";

export default function OrgsPage() {
  const ok = useRequireAuth();
  const { logout } = useAuth();
  const router = useRouter();
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      setOrgs(await apiGet<Org[]>("/orgs"));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (ok) load();
  }, [ok]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await apiPost<Org>("/orgs", { name, slug });
      setName("");
      setSlug("");
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  if (!ok) return <div className="p-8 text-slate-500">Loading…</div>;

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <PageHeader
        title="Your organizations"
        action={
          <Button variant="ghost" onClick={() => { logout(); router.replace("/login"); }}>
            Sign out
          </Button>
        }
      />

      <div className="grid gap-3">
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {!loading && orgs.length === 0 && (
          <p className="text-sm text-slate-500">No organizations yet — create your first below.</p>
        )}
        {orgs.map((o) => (
          <Link key={o.id} href={`/orgs/${o.id}/links`}>
            <Card className="transition hover:border-brand">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold">{o.name}</div>
                  <div className="text-sm text-slate-500">/{o.slug}</div>
                </div>
                <span className="text-xs uppercase text-slate-400">{o.plan}</span>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      <Card className="mt-8">
        <h2 className="mb-3 font-semibold">New organization</h2>
        <form onSubmit={create} className="space-y-3">
          <Field label="Name">
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label="Slug (lowercase, a-z 0-9 -)">
            <Input
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              pattern="[a-z0-9-]+"
              required
            />
          </Field>
          <ErrorText>{err}</ErrorText>
          <Button type="submit">Create organization</Button>
        </form>
      </Card>
    </main>
  );
}
