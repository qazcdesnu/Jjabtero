// @doc: docs/design/LibraryView.md#4-테스트
// @doc: docs/design/ReadingStatus.md#4-테스트

import { describe, expect, it, vi } from 'vitest'
import { ITEM_TYPE_LABELS, READ_STATUSES, formatDate, formatDateTime, readStatusInfo, timeKey } from './labels'

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

  it('서버 시각을 이 컴퓨터의 시간대로 날짜·시각으로 보이고, 시간대 표시가 없으면 UTC로 읽는다', () => {
    vi.stubEnv('TZ', 'Asia/Seoul')
    try {
      expect(formatDate('2026-11-01T05:25:29.123456')).toBe('2026-11-01')
      expect(formatDate('2026-11-17T19:48:12.197842')).toBe('2026-11-18')
      expect(formatDateTime('2026-11-17T19:48:12.197842')).toBe('2026-11-18 04:48')
      expect(formatDateTime('2026-11-17T19:48:12+00:00')).toBe('2026-11-18 04:48')
      expect(timeKey('2026-11-17T19:48:12')).toBe('2026-11-17T19:48:12.000Z')
      expect(timeKey('2026-11-17T20:48:12+01:00')).toBe('2026-11-17T19:48:12.000Z')
      expect(timeKey('2026-11-17T19:48:12') < timeKey('2026-11-17T19:48:13.5')).toBe(true)
      expect(formatDate('알 수 없음')).toBe('알 수 없음')
    } finally {
      vi.unstubAllEnvs()
    }
  })

  it('읽기 상태 세 가지의 이름과 색을 돌려주고, 모르는 값은 그대로 쓴다', () => {
    expect(READ_STATUSES.map((status) => status.value)).toEqual(['to-read', 'reading', 'read'])
    expect(readStatusInfo('reading')).toMatchObject({ label: '읽는 중', severity: 'info' })
    expect(readStatusInfo('done')).toEqual({ label: 'done', severity: 'secondary' })
  })
})
