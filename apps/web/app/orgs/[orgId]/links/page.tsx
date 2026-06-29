"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge, Button, Card, ErrorText, Field, Input, PageHeader, Select } from "@/components/ui";
import { apiGet, apiPost, PUBLIC_BASE } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { Link as SmartLink } from "@/lib/types";

export default function LinksPage() {
  const ok = useRequireAuth();
  const { orgId } = useParams<{ orgId: string }>();
  const [links, setLinks] = useState<SmartLink[]>([]);
  const [slug, setSlug] = useState("");
  const [type, setType] = useState("redirect");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      setLinks(await apiGet<SmartLink[]>(`/orgs/${orgId}/links`));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (ok) load();
  }, [ok, orgId]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await apiPost<SmartLink>(`/orgs/${orgId}/links`, {
        type,
        slug: slug.trim() || null,
      });
      setSlug("");
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  if (!ok) return null;

  return (
    <>
      <PageHeader title="Smart links" />
      <div className="grid gap-3">
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {!loading && links.length === 0 && (
          <p className="text-sm text-slate-500">No links yet — create one below.</p>
        )}
        {links.map((l) => (
          <Link key={l.id} href={`/orgs/${orgId}/links/${l.id}`}>
            <Card className="transition hover:border-brand">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-mono text-sm font-semibold">{l.code}</div>
                  <div className="text-xs text-slate-500">
                    {PUBLIC_BASE}/r/{l.code}
                    {l.slug ? ` · /${l.slug}` : ""}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge>{l.type}</Badge>
                  <Badge tone={l.is_active ? "green" : "amber"}>
                    {l.is_active ? "active" : "inactive"}
                  </Badge>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      <Card className="mt-8 max-w-lg">
        <h2 className="mb-3 font-semibold">New link</h2>
        <form onSubmit={create} className="space-y-3">
          <Field label="Type">
            <Select value={type} onChange={(e) => setType(e.target.value)}>
              <option value="redirect">redirect</option>
              <option value="multi">multi</option>
              <option value="landing">landing</option>
            </Select>
          </Field>
          <Field label="Vanity slug (optional)">
            <Input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="my-cafe" />
          </Field>
          <ErrorText>{err}</ErrorText>
          <Button type="submit">Create link</Button>
        </form>
      </Card>
    </>
  );
}
