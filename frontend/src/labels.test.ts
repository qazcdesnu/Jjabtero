// @doc: docs/design/LibraryView.md#4-테스트
// @doc: docs/design/ReadingStatus.md#4-테스트

import { describe, expect, it } from 'vitest'
import { ITEM_TYPE_LABELS, READ_STATUSES, formatDate, readStatusInfo } from './labels'

describe('labels', () => {
  it('모든 항목 종류에 한국어 이름이 있다', () => {
    expect(Object.keys(ITEM_TYPE_LABELS).sort()).toEqual([
      'book',
      'book-chapter',
      'conference-paper',
      'journal-article',
      'other',
      'preprint',
      'report',
      'thesis',
    ])
  })

  it('시각 문자열을 날짜로 줄인다', () => {
    expect(formatDate('2026-11-01T05:25:29.123456')).toBe('2026-11-01')
    expect(formatDate('2026-11-01T05:25:29+00:00')).toBe('2026-11-01')
  })

  it('읽기 상태 세 가지의 이름과 색을 돌려주고, 모르는 값은 그대로 쓴다', () => {
    expect(READ_STATUSES.map((status) => status.value)).toEqual(['to-read', 'reading', 'read'])
    expect(readStatusInfo('reading')).toMatchObject({ label: '읽는 중', severity: 'info' })
    expect(readStatusInfo('done')).toEqual({ label: 'done', severity: 'secondary' })
  })
})
