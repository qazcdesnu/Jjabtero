// @doc: docs/design/LibraryView.md#2-화면-상태
// @doc: docs/design/ReadingStatus.md#3-화면

// @doc: docs/design/LibraryView.md#2-화면-상태
export const ITEM_TYPE_LABELS: Record<string, string> = {
  'journal-article': '저널 논문',
  'conference-paper': '학회 논문',
  preprint: '프리프린트',
  book: '책',
  'book-chapter': '책의 장',
  thesis: '학위논문',
  report: '보고서',
  other: '그 밖',
}

// @doc: docs/design/LibraryView.md#2-화면-상태
export function formatDate(value: string): string {
  return value.slice(0, 10)
}

// @doc: docs/design/ReadingStatus.md#3-화면
export const READ_STATUSES = [
  { value: 'to-read', label: '읽을 것', severity: 'secondary' },
  { value: 'reading', label: '읽는 중', severity: 'info' },
  { value: 'read', label: '다 읽음', severity: 'success' },
] as const

// @doc: docs/design/ReadingStatus.md#3-화면
export function readStatusInfo(value: string): { label: string; severity: string } {
  return READ_STATUSES.find((status) => status.value === value) ?? { label: value, severity: 'secondary' }
}

