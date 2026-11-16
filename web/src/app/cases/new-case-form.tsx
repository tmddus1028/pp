"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";

// Attorneys work from the two filed documents. Cited publications are fetched by the backend
// (KIPRIS_FETCH_CITATIONS); the text-paste and 가상 예제 entry points stay in the API for tests only.
export function NewCaseForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(request: () => Promise<{ id: number }>, tab = "demo") {
    setBusy(true);
    setError("");
    try {
      const { id } = await request();
      router.push(`/cases/${id}/${tab}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    run(() => api("/cases", { method: "POST", body: form }));
  }

  return (
    <form className="stack" onSubmit={submit}>
      <fieldset className="form-grid" disabled={busy}>
        <label className="card">
          <b>1 · 특허 공보 PDF</b>
          <input type="file" name="patent" required accept=".pdf,.txt" />
        </label>
        <label className="card">
          <b>2 · 의견제출통지서 · XML 또는 PDF</b>
          <input type="file" name="office_action" required accept=".xml,.pdf" />
        </label>
      </fieldset>

      <div className="row">
        <button type="submit" className="button primary" disabled={busy}>
          분석 시작
        </button>
        <button
          type="button"
          className="button"
          disabled={busy}
          onClick={() => run(() => api("/cases/sample?reuse=true", { method: "POST" }))}
        >
          샘플 사건 불러오기
        </button>
        {busy && <span className="muted">분석하고 있습니다… 문서에 따라 몇 분 걸릴 수 있습니다.</span>}
      </div>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
