// @doc: docs/design/Reader.md#8-테스트

import { describe, expect, it } from 'vitest'
import {
  clampPage,
  fitWidthScale,
  nextZoom,
  pageAt,
  pageTops,
  positionAt,
  scrollTopFor,
  visiblePages,
} from './readerState'

const sizes = [
  { width: 600, height: 800 },
  { width: 600, height: 800 },
  { width: 600, height: 800 },
  { width: 600, height: 800 },
]

describe('readerState', () => {
  it('확대 단계를 한 칸씩 오르내리고 끝에서 멈춘다', () => {
    expect(nextZoom(1, 1)).toBe(1.25)
    expect(nextZoom(1, -1)).toBe(0.75)
    expect(nextZoom(1.1, 1)).toBe(1.25)
    expect(nextZoom(3, 1)).toBe(3)
    expect(nextZoom(0.5, -1)).toBe(0.5)
  })

  it('너비 맞춤은 가장 넓은 쪽을 칸 너비에 맞추고 범위를 넘지 않는다', () => {
    expect(fitWidthScale(sizes, 632)).toBe(1)
    expect(fitWidthScale(sizes, 100)).toBe(0.5)
    expect(fitWidthScale(sizes, 10000)).toBe(3)
  })

  it('쪽 위치는 쪽 높이와 간격으로 쌓인다', () => {
    expect(pageTops(sizes, 0.5)).toEqual([16, 432, 848, 1264])
  })

  it('스크롤 위치의 쪽과 보이는 쪽(앞뒤 한 쪽 포함)을 찾는다', () => {
    const tops = pageTops(sizes, 1)
    const heights = sizes.map((size) => size.height)
    expect(pageAt(0, tops)).toBe(1)
    expect(pageAt(tops[2], tops)).toBe(3)
    expect(visiblePages(tops[1] + 10, 500, tops, heights)).toEqual([1, 2, 3])
    expect(visiblePages(0, 500, tops, heights)).toEqual([1, 2])
  })

  it('쪽 번호를 범위 안으로 맞춘다', () => {
    expect(clampPage(0, 4)).toBe(1)
    expect(clampPage(9, 4)).toBe(4)
    expect(clampPage(2.4, 4)).toBe(2)
    expect(clampPage(3, 0)).toBe(1)
  })

  it('읽던 위치(쪽, 쪽 안 비율)와 스크롤 위치를 서로 바꾼다', () => {
    const tops = pageTops(sizes, 1)
    const heights = sizes.map((size) => size.height)
    const position = positionAt(tops[2] + 200, tops, heights)
    expect(position).toEqual({ page: 3, offset: 0.25 })
    expect(scrollTopFor(position.page, position.offset, tops, heights)).toBe(tops[2] + 200)
    expect(scrollTopFor(99, 2, tops, heights)).toBe(tops[3] + 800)
  })
})
