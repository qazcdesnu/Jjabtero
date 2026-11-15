// @doc: docs/design/ReaderCitations.md#6-테스트

import { describe, expect, it } from 'vitest'
import { anchorFromDest, isCitationDest, linkRect, referenceEntryText, type Anchor, type TextPiece } from './citationLinks'

const anchors: Anchor[] = [
  { name: 'cite.a', page: 11, x: 108, y: 453.4 },
  { name: 'cite.b', page: 11, x: 108, y: 420 },
  { name: 'cite.c', page: 11, x: 320, y: 453.4 },
  { name: 'cite.z', page: 10, x: 108, y: 300 },
]

const pieces: TextPiece[] = [
  { str: 'recurrent nets: the difficulty', x: 130, y: 462.3 },
  { str: '[13] Sepp Hochreiter and Jürgen Schmidhuber. Long short-term mem-', x: 108, y: 442.5 },
  { str: 'ory.', x: 130, y: 431.6, width: 20 },
  { str: 'Neural computation,', x: 152.5, y: 431.6, width: 75 },
  { str: '9(8):1735–1780, 1997.', x: 230, y: 431.6 },
  { str: '[22] Other column entry.', x: 320, y: 442.5 },
  { str: '[14] Next entry starts here.', x: 108, y: 409 },
]

describe('isCitationDest', () => {
  it('cite.로 시작하는 이름만 인용 링크다', () => {
    expect(isCitationDest('cite.hochreiter1997')).toBe(true)
    expect(isCitationDest('section.2')).toBe(false)
    expect(isCitationDest([{ num: 1 }])).toBe(false)
  })
})

describe('linkRect', () => {
  it('화면 좌표의 사각형을 쪽 크기에 대한 비율로 바꾼다', () => {
    expect(linkRect([100, 220, 60, 200], 200, 400)).toEqual({ x: 0.3, y: 0.5, w: 0.2, h: 0.05 })
  })
})

describe('anchorFromDest', () => {
  it('XYZ는 왼쪽·위 좌표를, FitH는 위 좌표만, 그 밖에는 좌표 없이 둔다', () => {
    expect(anchorFromDest('cite.a', 11, [{ num: 1 }, { name: 'XYZ' }, 108, 453.4, null])).toEqual(anchors[0])
    expect(anchorFromDest('cite.a', 3, [{ num: 1 }, { name: 'FitH' }, 500])).toEqual({ name: 'cite.a', page: 3, x: null, y: 500 })
    expect(anchorFromDest('cite.a', 3, [{ num: 1 }, { name: 'Fit' }])).toEqual({ name: 'cite.a', page: 3, x: null, y: null })
  })
})

describe('referenceEntryText', () => {
  it('같은 단에서 이 목적지부터 다음 목적지 전까지 잇고, 떨어진 조각 사이에 빈칸을 넣으며, 하이픈으로 끊긴 낱말을 붙인다', () => {
    expect(referenceEntryText(anchors[0], anchors, pieces, 612)).toBe(
      '[13] Sepp Hochreiter and Jürgen Schmidhuber. Long short-term memory. Neural computation, 9(8):1735–1780, 1997.',
    )
  })

  it('오른쪽 단의 항목은 그 단의 글만 읽는다', () => {
    expect(referenceEntryText(anchors[2], anchors, pieces, 612)).toBe('[22] Other column entry.')
  })

  it('아래 목적지가 없으면 80pt 아래까지 읽고, 위 좌표가 없으면 빈 글이다', () => {
    expect(referenceEntryText(anchors[1], anchors, pieces, 612)).toBe('[14] Next entry starts here.')
    expect(referenceEntryText({ name: 'cite.q', page: 11, x: null, y: null }, anchors, pieces, 612)).toBe('')
  })

  it('600자에서 자른다', () => {
    const long = [{ str: 'x'.repeat(700), x: 108, y: 450 }]
    expect(referenceEntryText(anchors[0], anchors, long, 612)).toHaveLength(600)
  })
})
