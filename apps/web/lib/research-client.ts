export async function researchJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {...init, cache:'no-store'});
  if (!response.ok) {
    const detail = await response.json().catch(() => null) as {detail?: unknown; code?: unknown} | null;
    const messages: Record<number,string> = {
      401:'Your research session has expired. Sign in again; unsaved fields are still here.',
      403:'Your role cannot perform this action. A project administrator is required.',
      404:'This project, case or source is not available to your account.',
      409:'The identifier already exists, the source is ineligible, or the record changed. Review the current record before retrying.',
      412:'The record changed while you were editing. Reload the saved profile before retrying.',
      422:'Some fields are invalid. Check values, units, dates and source references.',
      502:'The research service is unavailable. Your entered fields have been retained; retry when it is available.',
    };
    const safeCode = typeof detail?.code === 'string' && /^[A-Z_]{1,80}$/.test(detail.code) ? ` (${detail.code})` : '';
    throw new Error((messages[response.status] ?? `The request failed (${response.status}). Please retry.`) + safeCode);
  }
  return response.json() as Promise<T>;
}
export function researchError(error: unknown): string { return error instanceof Error ? error.message : 'The request could not be completed. Retry without changing your source record.'; }
