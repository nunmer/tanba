"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Button, Card, ErrorText, Field, Input, PageHeader } from "@/components/ui";
import { apiGet, apiPatch } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { Org } from "@/lib/types";

export default function SettingsPage() {
  const ok = useRequireAuth();
  const { orgId } = useParams<{ orgId: string }>();
  const [org, setOrg] = useState<Org | null>(null);
  const [name, setName] = useState("");
  const [branding, setBranding] = useState("{}");
  const [err, setErr] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!ok) return;
    apiGet<Org>(`/orgs/${orgId}`).then((o) => {
      setOrg(o);
      setName(o.name);
    });
  }, [ok, orgId]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setSaved(false);
    let brandingObj: unknown = {};
    if (branding.trim()) {
      try {
        brandingObj = JSON.parse(branding);
      } catch {
        setErr("Branding must be valid JSON.");
        return;
      }
    }
    try {
      await apiPatch(`/orgs/${orgId}`, { name, branding: brandingObj });
      setSaved(true);
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  if (!ok || !org) return <div className="text-slate-500">Loading…</div>;
  return (
    <>
      <PageHeader title="Organization settings" />
      <Card className="max-w-lg">
        <form onSubmit={save} className="space-y-3">
          <Field label="Name">
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label="Slug (read-only)">
            <Input value={org.slug} disabled />
          </Field>
          <Field label='Branding JSON (e.g. {"theme":{"accent":"#2f6df6"}})'>
            <textarea
              value={branding}
              onChange={(e) => setBranding(e.target.value)}
              rows={4}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm outline-none focus:border-brand focus:ring-1 focus:ring-brand"
            />
          </Field>
          <ErrorText>{err}</ErrorText>
          {saved && <p className="text-sm text-green-600">Saved.</p>}
          <Button type="submit">Save</Button>
        </form>
      </Card>
    </>
  );
}
