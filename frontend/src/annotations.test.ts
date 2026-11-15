// @doc: docs/design/Reader.md#8-테스트

import { describe, expect, it } from 'vitest'
import { colorFill, hitTest, normalizeRects } from './annotations'

const page = { left: 100, top: 50, width: 1000, height: 2000 }

describe('normalizeRects', () => {
  it('화면 좌표를 쪽 비율로 바꾸고 같은 줄의 붙은 조각을 합친다', () => {
    const rects = normalizeRects(
      [
        { left: 200, top: 1050, width: 100, height: 20 },
        { left: 300, top: 1051, width: 200, height: 20 },
        { left: 200, top: 1090, width: 50, height: 20 },
        { left: 200, top: 1090, width: 0.2, height: 20 },
      ],
      page,
    )
    expect(rects).toEqual([
      { x: 0.1, y: 0.5, w: 0.3, h: 0.0105 },
      { x: 0.1, y: 0.52, w: 0.05, h: 0.01 },
    ])
  })

  it('쪽 밖 조각은 버리고 걸친 조각은 쪽 안으로 자른다', () => {
    const rects = normalizeRects(
      [
        { left: 2000, top: 100, width: 100, height: 20 },
        { left: 1050, top: 60, width: 100, height: 20 },
      ],
      page,
    )
    expect(rects).toEqual([{ x: 0.95, y: 0.005, w: 0.05, h: 0.01 }])
  })
})

describe('hitTest', () => {
  const annotations = [
    { id: 1, page: 2, rects: [{ x: 0.1, y: 0.1, w: 0.5, h: 0.1 }] },
    { id: 2, page: 2, rects: [{ x: 0.3, y: 0.15, w: 0.5, h: 0.1 }] },
    { id: 3, page: 3, rects: [{ x: 0, y: 0, w: 1, h: 1 }] },
  ]

  it('같은 쪽에서 점을 품은 주석 중 나중 것을 돌려준다', () => {
    expect(hitTest(2, { x: 0.35, y: 0.17 }, annotations)?.id).toBe(2)
    expect(hitTest(2, { x: 0.15, y: 0.12 }, annotations)?.id).toBe(1)
    expect(hitTest(2, { x: 0.95, y: 0.95 }, annotations)).toBeNull()
  })
})

describe('colorFill', () => {
  it('모르는 색은 노랑으로 그린다', () => {
    expect(colorFill('green')).toContain('222')
    expect(colorFill('red')).toBe(colorFill('yellow'))
  })
})
