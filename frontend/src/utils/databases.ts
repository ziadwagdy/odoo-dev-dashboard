/** Names of the databases in a `GET /api/db/<project>/list` response.
 *  The API returns `{ databases: [{ name, size, ... }] }`; a bare array is tolerated too. */
export function databaseNames(data: unknown): string[] {
  const list = Array.isArray(data) ? data : (data as { databases?: unknown } | null)?.databases
  if (!Array.isArray(list)) return []
  return list
    .map((d) => (d && typeof d === 'object' ? (d as { name?: unknown }).name : undefined))
    .filter((n): n is string => typeof n === 'string' && n.length > 0)
}
