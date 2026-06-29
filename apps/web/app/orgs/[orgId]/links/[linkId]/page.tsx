"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge, Button, Card, ErrorText, Field, Input, PageHeader, Select } from "@/components/ui";
import { apiDelete, apiGet, apiPatch, apiPost, PUBLIC_BASE } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { DESTINATION_KINDS, type Destination, type Link as SmartLink } from "@/lib/types";

export default function LinkDetailPage() {
  const ok = useRequireAuth();
  const { orgId, linkId } = useParams<{ orgId: string; linkId: string }>();
  const router = useRouter();
  const [link, setLink] = useState<SmartLink | null>(null);
  const [dests, setDests] = useState<Destination[]>([]);
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);

  async function load() {
    try {
      const [l, d] = await Promise.all([
        apiGet<SmartLink>(`/links/${linkId}`),
        apiGet<Destination[]>(`/links/${linkId}/destinations`),
      ]);
      setLink(l);
      setDests(d);
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  useEffect(() => {
    if (ok) load();
  }, [ok, linkId]);

  if (!ok || !link) return <div className="text-slate-500">Loading…</div>;

  const publicUrl = `${PUBLIC_BASE}/r/${link.code}`;

  async function toggleActive() {
    await apiPatch(`/links/${linkId}`, { is_active: !link!.is_active });
    load();
  }

  async function removeLink() {
    if (!confirm("Delete this link and all its destinations?")) return;
    await apiDelete(`/links/${linkId}`);
    router.replace(`/orgs/${orgId}/links`);
  }

  async function copy() {
    await navigator.clipboard.writeText(publicUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <>
      <PageHeader
        title={`Link ${link.code}`}
        action={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={toggleActive}>
              {link.is_active ? "Deactivate" : "Activate"}
            </Button>
            <Button variant="danger" onClick={removeLink}>
              Delete
            </Button>
          </div>
        }
      />

      <Card className="mb-6">
        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
          Permanent public URL
        </div>
        <div className="mt-1 flex items-center gap-3">
          <code className="rounded bg-slate-100 px-2 py-1 text-sm">{publicUrl}</code>
          <Button variant="ghost" onClick={copy}>
            {copied ? "Copied!" : "Copy"}
          </Button>
          <a
            href={publicUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold text-brand"
          >
            Test ↗
          </a>
        </div>
        <div className="mt-3 flex gap-2 text-sm">
          <Badge>{link.type}</Badge>
          <Badge tone={link.is_active ? "green" : "amber"}>
            {link.is_active ? "active" : "inactive"}
          </Badge>
          {link.slug && <Badge>/{link.slug}</Badge>}
        </div>
      </Card>

      <h2 className="mb-3 text-lg font-semibold">Destinations (routing table)</h2>
      <p className="mb-4 text-sm text-slate-500">
        Lowest <strong>priority</strong> number wins among matching rules; equal priorities split by{" "}
        <strong>weight</strong> (A/B). Leave the match empty for a catch-all default.
      </p>

      <div className="mb-6 grid gap-2">
        {dests.length === 0 && <p className="text-sm text-slate-500">No destinations yet.</p>}
        {dests.map((d) => (
          <DestinationRow key={d.id} dest={d} onChange={load} />
        ))}
      </div>

      <ErrorText>{err}</ErrorText>
      <DestinationForm linkId={linkId} onCreated={load} />
    </>
  );
}

function DestinationRow({ dest, onChange }: { dest: Destination; onChange: () => void }) {
  async function toggle() {
    await apiPatch(`/destinations/${dest.id}`, { is_active: !dest.is_active });
    onChange();
  }
  async function remove() {
    await apiDelete(`/destinations/${dest.id}`);
    onChange();
  }
  return (
    <Card>
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold">{dest.label || dest.kind}</span>
            <Badge>{dest.kind}</Badge>
            <Badge tone={dest.is_active ? "green" : "amber"}>
              {dest.is_active ? "active" : "off"}
            </Badge>
          </div>
          <div className="truncate text-sm text-slate-500">{dest.url}</div>
          <div className="mt-1 text-xs text-slate-400">
            priority {dest.priority} · weight {dest.weight}
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button variant="ghost" onClick={toggle}>
            {dest.is_active ? "Disable" : "Enable"}
          </Button>
          <Button variant="danger" onClick={remove}>
            Delete
          </Button>
        </div>
      </div>
    </Card>
  );
}

function DestinationForm({ linkId, onCreated }: { linkId: string; onCreated: () => void }) {
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const [kind, setKind] = useState<string>("url");
  const [priority, setPriority] = useState(100);
  const [weight, setWeight] = useState(1);
  const [matchText, setMatchText] = useState("");
  const [err, setErr] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    let match: unknown = null;
    if (matchText.trim()) {
      try {
        match = JSON.parse(matchText);
      } catch {
        setErr("Match must be valid JSON, e.g. {\"platform\":\"ios\"}");
        return;
      }
    }
    try {
      await apiPost(`/links/${linkId}/destinations`, {
        url,
        label,
        kind,
        priority,
        weight,
        match,
      });
      setUrl("");
      setLabel("");
      setMatchText("");
      onCreated();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <Card className="max-w-2xl">
      <h3 className="mb-3 font-semibold">Add destination</h3>
      <form onSubmit={submit} className="space-y-3">
        <Field label="Target URL">
          <Input value={url} onChange={(e) => setUrl(e.target.value)} required placeholder="https://2gis.kz/..." />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Label">
            <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="2GIS review" />
          </Field>
          <Field label="Kind">
            <Select value={kind} onChange={(e) => setKind(e.target.value)}>
              {DESTINATION_KINDS.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Priority (lower wins)">
            <Input
              type="number"
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
            />
          </Field>
          <Field label="Weight (A/B)">
            <Input
              type="number"
              min={1}
              value={weight}
              onChange={(e) => setWeight(Number(e.target.value))}
            />
          </Field>
        </div>
        <Field label='Match rule JSON (optional, e.g. {"platform":"ios"})'>
          <Input value={matchText} onChange={(e) => setMatchText(e.target.value)} placeholder="leave empty = default" />
        </Field>
        <ErrorText>{err}</ErrorText>
        <Button type="submit">Add destination</Button>
      </form>
    </Card>
  );
}
