export const ISSUE_CATEGORIES = ['water','sanitation','drainage','waste','access','electricity','other'] as const
export type IssueCategory = typeof ISSUE_CATEGORIES[number]
export type CitizenIssue = { id: string; category: IssueCategory; description: string; ward: string | null; location: string | null; latitude: number | null; longitude: number | null; report_date: string; reported_at: string; updated_at: string; status: 'submitted'|'under_review'|'resolved'; official_submission: false; verification_status: 'self_reported'; attachment: { filename: string; content_type: string; sha256: string } | null; resolution_note?: string }
export type IssueSummary = { total: number; open: number; by_status: Record<CitizenIssue['status'], number>; recent: CitizenIssue[]; official_submission: false }

/** A successful HTTP status alone does not confirm that a report was persisted. */
export function confirmedIssue(value: unknown): CitizenIssue {
  const row = value as Partial<CitizenIssue> | null
  if (!row || typeof row !== 'object' || typeof row.id !== 'string' || !/^ISS-[A-F0-9]{12}$/.test(row.id) ||
      !ISSUE_CATEGORIES.includes(row.category as IssueCategory) || !['submitted','under_review','resolved'].includes(row.status || '') ||
      typeof row.description !== 'string' || row.description.trim().length < 10 || row.official_submission !== false || row.verification_status !== 'self_reported' ||
      !row.report_date || !Number.isFinite(Date.parse(row.report_date)) || !row.reported_at || !Number.isFinite(Date.parse(row.reported_at))) {
    throw new Error('civic.persistenceUnconfirmed')
  }
  return row as CitizenIssue
}
