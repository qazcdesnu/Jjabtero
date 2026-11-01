// @doc: docs/design/LibraryView.md#2-화면-상태

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
