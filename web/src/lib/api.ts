export class ApiError extends Error {}

/** Same-origin call through the Next rewrite; surfaces FastAPI's `detail` message. */
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch("/api" + path, init);
  } catch {
    throw new ApiError("API에 연결할 수 없습니다. backend 실행 상태를 확인하세요.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new ApiError(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg: string }) => d.msg).join(", ")
          : "API 응답을 확인할 수 없습니다. 서버 상태를 확인하세요.",
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
