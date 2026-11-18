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
export function timeKey(value: string): string {
  // 정렬에 쓰는 UTC ISO 문자열. 서버 시각의 꼴(소수점, 시간대 표시)이 달라도 글자 순서가 시각 순서가 된다.
  const time = serverTime(value)
  return Number.isNaN(time) ? value : new Date(time).toISOString()
}

function serverTime(value: string): number {
  // 서버는 UTC 시각을 시간대 표시 없이 주기도 한다(`2026-11-17T19:48:12.197842`). 그때는 UTC로 읽는다.
  const zoned = /(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`
  return Date.parse(zoned)
}

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

// @doc: docs/design/LibraryView.md#2-화면-상태
export function formatDate(value: string): string {
  const time = new Date(serverTime(value))
  if (Number.isNaN(time.getTime())) return value.slice(0, 10)
  return `${time.getFullYear()}-${pad(time.getMonth() + 1)}-${pad(time.getDate())}`
}

// @doc: docs/design/LibraryView.md#2-화면-상태
export function formatShortDate(value: string): string {
  // 좁은 표 칸에 쓰는 두 자리 연도 날짜(`26-11-18`)
  const date = formatDate(value)
  return /^\d{4}-/.test(date) ? date.slice(2) : date
}

// @doc: docs/design/LibraryView.md#2-화면-상태
export function formatDateTime(value: string): string {
  const time = new Date(serverTime(value))
  if (Number.isNaN(time.getTime())) return value
  return `${formatDate(value)} ${pad(time.getHours())}:${pad(time.getMinutes())}`
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

