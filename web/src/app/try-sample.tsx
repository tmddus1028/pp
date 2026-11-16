"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

// Same request as "샘플 사건 불러오기" in the 새 사건 등록 dialog on /cases: a real case (0844) saved with AI advice and a draft.
export function TrySample() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function start() {
    setBusy(true);
    setError("");
    try {
      const { id } = await api<{ id: number }>("/cases/sample?reuse=true", { method: "POST" });
      router.push(`/cases/${id}/demo`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="lp-try">
      <button type="button" className="button lp-cta" disabled={busy} onClick={start}>
        {busy ? "불러오는 중…" : "샘플 사건으로 체험하기"}
      </button>
      <p className="hint">샘플은 실제 특허 사건입니다.</p>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
