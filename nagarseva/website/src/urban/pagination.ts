/** Fetch a stable bounded snapshot; partial lists must never look complete. */
export async function collectPages<T extends { id: string }>(
  load: (page: number, pageSize: number) => Promise<{ items: T[]; total: number }>,
  pageSize = 1000,
  maximum = 20000,
): Promise<T[]> {
  const rows: T[] = [], seen = new Set<string>()
  let total: number | undefined
  for (let page = 1; ; page++) {
    const result = await load(page, pageSize)
    if (!Number.isSafeInteger(result.total) || result.total < 0 || result.total > maximum) {
      throw new Error(`Dataset exceeds the supported ${maximum.toLocaleString()} record limit or has an invalid count.`)
    }
    if (total !== undefined && total !== result.total) throw new Error('Source snapshot changed while loading. Retry the data connection.')
    total = result.total
    if (result.items.length !== Math.min(pageSize, total - rows.length)) throw new Error('The API returned an incomplete page. Retry the data connection.')
    for (const item of result.items) {
      if (!item.id || seen.has(item.id)) throw new Error('Duplicate source IDs across API pages. Retry the data connection.')
      seen.add(item.id); rows.push(item)
    }
    if (rows.length === total) return rows
  }
}
