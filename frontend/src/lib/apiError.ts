// Extrae el `detail` (string) de un error de Axios cuando el backend lo provee.
// Devuelve null si no hay detail string usable; el caller usa su mensaje genérico.
export function getApiErrorDetail(err: unknown): string | null {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return null;
}
