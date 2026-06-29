"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge, Button, Card, ErrorText, Field, Input, PageHeader, Select } from "@/components/ui";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { Member } from "@/lib/types";

const ROLES = ["owner", "admin", "member"];

export default function MembersPage() {
  const ok = useRequireAuth();
  const { orgId } = useParams<{ orgId: string }>();
  const [items, setItems] = useState<Member[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [err, setErr] = useState("");

  async function load() {
    try {
      setItems(await apiGet<Member[]>(`/orgs/${orgId}/members`));
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  useEffect(() => {
    if (ok) load();
  }, [ok, orgId]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await apiPost(`/orgs/${orgId}/members`, { email, role });
      setEmail("");
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function remove(userId: string) {
    setErr("");
    try {
      await apiDelete(`/orgs/${orgId}/members/${userId}`);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  if (!ok) return null;
  return (
    <>
      <PageHeader title="Members" />
      <div className="mb-6 grid gap-2">
        {items.map((m) => (
          <Card key={m.id}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-semibold">{m.email}</span>
                <Badge>{m.role}</Badge>
              </div>
              <Button variant="danger" onClick={() => remove(m.user_id)}>
                Remove
              </Button>
            </div>
          </Card>
        ))}
      </div>
      <Card className="max-w-lg">
        <h2 className="mb-3 font-semibold">Add member (must already have an account)</h2>
        <form onSubmit={add} className="space-y-3">
          <Field label="Email">
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Role">
            <Select value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
          </Field>
          <ErrorText>{err}</ErrorText>
          <Button type="submit">Add member</Button>
        </form>
      </Card>
    </>
  );
}
