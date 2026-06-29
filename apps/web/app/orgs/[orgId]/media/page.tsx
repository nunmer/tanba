"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge, Button, Card, ErrorText, Field, Input, PageHeader, Select } from "@/components/ui";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { MEDIUM_TYPES, type Link as SmartLink, type Media } from "@/lib/types";

export default function MediaPage() {
  const ok = useRequireAuth();
  const { orgId } = useParams<{ orgId: string }>();
  const [items, setItems] = useState<Media[]>([]);
  const [links, setLinks] = useState<SmartLink[]>([]);
  const [smartlinkId, setSmartlinkId] = useState("");
  const [mediumType, setMediumType] = useState<string>("nfc_card");
  const [serial, setSerial] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    try {
      const [m, l] = await Promise.all([
        apiGet<Media[]>(`/orgs/${orgId}/media`),
        apiGet<SmartLink[]>(`/orgs/${orgId}/links`),
      ]);
      setItems(m);
      setLinks(l);
      if (!smartlinkId && l.length) setSmartlinkId(l[0].id);
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
      await apiPost(`/orgs/${orgId}/media`, {
        smartlink_id: smartlinkId,
        medium_type: mediumType,
        serial: serial || null,
      });
      setSerial("");
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function remove(id: string) {
    await apiDelete(`/media/${id}`);
    load();
  }

  if (!ok) return null;
  const codeFor = (id: string) => links.find((l) => l.id === id)?.code ?? "—";

  return (
    <>
      <PageHeader title="Physical media" />
      <div className="mb-6 grid gap-2">
        {items.length === 0 && <p className="text-sm text-slate-500">No media provisioned.</p>}
        {items.map((m) => (
          <Card key={m.id}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge>{m.medium_type}</Badge>
                <span className="text-sm text-slate-600">{m.serial || "no serial"}</span>
                <span className="font-mono text-xs text-slate-400">→ {codeFor(m.smartlink_id)}</span>
              </div>
              <Button variant="danger" onClick={() => remove(m.id)}>
                Delete
              </Button>
            </div>
          </Card>
        ))}
      </div>
      <Card className="max-w-lg">
        <h2 className="mb-3 font-semibold">Provision media</h2>
        {links.length === 0 ? (
          <p className="text-sm text-slate-500">Create a link first, then attach media to it.</p>
        ) : (
          <form onSubmit={create} className="space-y-3">
            <Field label="Smart link">
              <Select value={smartlinkId} onChange={(e) => setSmartlinkId(e.target.value)}>
                {links.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.code}
                    {l.slug ? ` (/${l.slug})` : ""}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Medium type">
              <Select value={mediumType} onChange={(e) => setMediumType(e.target.value)}>
                {MEDIUM_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Serial (optional)">
              <Input value={serial} onChange={(e) => setSerial(e.target.value)} />
            </Field>
            <ErrorText>{err}</ErrorText>
            <Button type="submit">Provision</Button>
          </form>
        )}
      </Card>
    </>
  );
}
