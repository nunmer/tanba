"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function OrgIndex() {
  const { orgId } = useParams<{ orgId: string }>();
  const router = useRouter();
  useEffect(() => {
    router.replace(`/orgs/${orgId}/links`);
  }, [orgId, router]);
  return null;
}
