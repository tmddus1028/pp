"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { api, json } from "@/lib/api";

type Mode = "file" | "text";

export default function NewCasePage() {
  const router = useRouter();
  const [jurisdiction, setJurisdiction] = useState<"US" | "KR">("US");
  const [mode, setMode] = useState<Mode>("file");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const korean = jurisdiction === "KR";

  async function run(request: () => Promise<{ id: number }>) {
    setBusy(true);
    setError("");
    try {
      const { id } = await request();
      router.push(`/cases/${id}/review`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const query = `?jurisdiction=${jurisdiction}`;
    if (mode === "file") {
      if (!(form.get("title") as string)?.trim()) form.delete("title");
      if ((form.getAll("references") as File[]).every((f) => !f.size)) form.delete("references");
      run(() => api("/cases" + query, { method: "POST", body: form }));
    } else {
      run(() =>
        api(
          "/cases/text" + query,
          json("POST", { patent_text: form.get("patent_text"), office_action_text: form.get("office_action_text") }),
        ),
      );
    }
  }

  return (
    <>
      <header className="page-header">
        <h1>새 사건</h1>
      </header>
      <form className="stack" onSubmit={submit}>
        <fieldset className="row" disabled={busy}>
          <legend>특허 관할</legend>
          {(["US", "KR"] as const).map((value) => (
            <label key={value}>
              <input type="radio" checked={jurisdiction === value} onChange={() => setJurisdiction(value)} />{" "}
              {value === "US" ? "미국 특허" : "한국 특허"}
            </label>
          ))}
        </fieldset>
        <fieldset className="row" disabled={busy}>
          <legend>입력 방법</legend>
          {(["file", "text"] as const).map((value) => (
            <label key={value}>
              <input type="radio" checked={mode === value} onChange={() => setMode(value)} />{" "}
              {value === "file" ? "파일 업로드" : "텍스트 입력"}
            </label>
          ))}
        </fieldset>

        {/* key resets inputs when the jurisdiction changes, like the Streamlit upload did. */}
        <fieldset className="grid-2" disabled={busy} key={jurisdiction + mode}>
          {mode === "file" ? (
            <>
              <label className="card">
                <b>01 · {korean ? "명세서·청구범위" : "Patent / Claims"}</b>
                <input type="file" name="patent" required accept={korean ? ".pdf,.txt" : ".pdf,.txt,.json"} />
              </label>
              <label className="card">
                <b>02 · {korean ? "의견제출통지서 XML / PDF" : "Office Action"}</b>
                <input type="file" name="office_action" required accept={korean ? ".xml,.pdf" : ".pdf,.txt,.json"} />
              </label>
              {korean && (
                <label className="card">
                  <b>인용발명 원문 (선택, 최대 10개)</b>
                  <input type="file" name="references" multiple accept=".pdf" />
                </label>
              )}
              <label className="card">
                <b>사건 이름 (선택)</b>
                <input name="title" maxLength={200} placeholder="비우면 특허 파일 이름" />
              </label>
            </>
          ) : (
            <>
              <label className="card">
                <b>01 · {korean ? "명세서·청구범위" : "Patent / Claims"}</b>
                <textarea name="patent_text" rows={14} required />
              </label>
              <label className="card">
                <b>02 · {korean ? "의견제출통지서 (XML 전체 또는 본문)" : "Office Action"}</b>
                <textarea name="office_action_text" rows={14} required />
              </label>
            </>
          )}
        </fieldset>

        <div className="row">
          <button type="submit" className="button primary" disabled={busy}>
            분석 시작
          </button>
          <button
            type="button"
            className="button"
            disabled={busy}
            onClick={() => run(() => api(`/cases/demo?jurisdiction=${jurisdiction}`, { method: "POST" }))}
          >
            예제 분석 · 가상 문서
          </button>
          {busy && <span className="muted">청구항과 거절 사유를 분석하고 있습니다… 문서에 따라 몇 분 걸릴 수 있습니다.</span>}
        </div>
        {error && <p className="error">{error}</p>}
        <p className="muted">PDF 원본은 변경하지 않습니다. 분석 결과와 원본 PDF는 사건으로 저장됩니다.</p>
      </form>
    </>
  );
}
