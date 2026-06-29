"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Button, Card, ErrorText, Field, Input, PageHeader } from "@/components/ui";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { Branch } from "@/lib/types";

export default function BranchesPage() {
  const ok = useRequireAuth();
  const { orgId } = useParams<{ orgId: string }>();
  const [items, setItems] = useState<Branch[]>([]);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [timezone, setTimezone] = useState("Asia/Almaty");
  const [err, setErr] = useState("");

  async function load() {
    try {
      setItems(await apiGet<Branch[]>(`/orgs/${orgId}/branches`));
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  useEffect(() => {
    if (ok) load();
  }, [ok, orgId]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await apiPost(`/orgs/${orgId}/branches`, { name, address: address || null, timezone });
      setName("");
      setAddress("");
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function remove(id: string) {
    await apiDelete(`/branches/${id}`);
    load();
  }

  if (!ok) return null;
  return (
    <>
      <PageHeader title="Branches" />
      <div className="mb-6 grid gap-2">
        {items.length === 0 && <p className="text-sm text-slate-500">No branches yet.</p>}
        {items.map((b) => (
          <Card key={b.id}>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold">{b.name}</div>
                <div className="text-sm text-slate-500">
                  {b.address || "—"} · {b.timezone}
                </div>
              </div>
              <Button variant="danger" onClick={() => remove(b.id)}>
                Delete
              </Button>
            </div>
          </Card>
        ))}
      </div>
      <Card className="max-w-lg">
        <h2 className="mb-3 font-semibold">New branch</h2>
        <form onSubmit={create} className="space-y-3">
          <Field label="Name">
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label="Address">
            <Input value={address} onChange={(e) => setAddress(e.target.value)} />
          </Field>
          <Field label="Timezone">
            <Input value={timezone} onChange={(e) => setTimezone(e.target.value)} />
          </Field>
          <ErrorText>{err}</ErrorText>
          <Button type="submit">Create branch</Button>
        </form>
      </Card>
    </>
  );
}
