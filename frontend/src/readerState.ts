// @doc: docs/design/Reader.md#6-화면

// @doc: docs/design/Reader.md#6-화면
export const ZOOM_STEPS = [0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3] as const

// @doc: docs/design/Reader.md#6-화면
export const PAGE_GAP = 16

// @doc: docs/design/Reader.md#6-화면
export interface PageSize {
  width: number
  height: number
}

// @doc: docs/design/Reader.md#6-화면
export function nextZoom(current: number, direction: 1 | -1): number {
  if (direction > 0) return ZOOM_STEPS.find((step) => step > current + 1e-6) ?? ZOOM_STEPS[ZOOM_STEPS.length - 1]
  return [...ZOOM_STEPS].reverse().find((step) => step < current - 1e-6) ?? ZOOM_STEPS[0]
}

// @doc: docs/design/Reader.md#6-화면
export function fitWidthScale(sizes: PageSize[], containerWidth: number, padding = 32): number {
  const widest = Math.max(...sizes.map((size) => size.width), 1)
  const scale = (containerWidth - padding) / widest
  return Math.min(Math.max(scale, ZOOM_STEPS[0]), ZOOM_STEPS[ZOOM_STEPS.length - 1])
}

// @doc: docs/design/Reader.md#6-화면
export function pageTops(sizes: PageSize[], scale: number, gap = PAGE_GAP): number[] {
  const tops: number[] = []
  let top = gap
  for (const size of sizes) {
    tops.push(top)
    top += size.height * scale + gap
  }
  return tops
}

// @doc: docs/design/Reader.md#6-화면
export function clampPage(page: number, total: number): number {
  if (total < 1) return 1
  return Math.min(Math.max(Math.round(page), 1), total)
}

// @doc: docs/design/Reader.md#6-화면
export function pageAt(scrollTop: number, tops: number[]): number {
  let page = 1
  for (let index = 0; index < tops.length; index += 1) {
    if (tops[index] <= scrollTop + 1) page = index + 1
    else break
  }
  return page
}

// @doc: docs/design/Reader.md#6-화면
export function visiblePages(
  scrollTop: number,
  viewportHeight: number,
  tops: number[],
  heights: number[],
  margin = 1,
): number[] {
  const bottom = scrollTop + viewportHeight
  const visible = tops
    .map((top, index) => ({ page: index + 1, top, end: top + heights[index] }))
    .filter((page) => page.end >= scrollTop && page.top <= bottom)
    .map((page) => page.page)
  if (visible.length === 0) return []
  const first = Math.max(visible[0] - margin, 1)
  const last = Math.min(visible[visible.length - 1] + margin, tops.length)
  return Array.from({ length: last - first + 1 }, (_, index) => first + index)
}

// @doc: docs/design/Reader.md#4-데이터
export function positionAt(scrollTop: number, tops: number[], heights: number[]): { page: number; offset: number } {
  const page = pageAt(scrollTop, tops)
  const height = heights[page - 1] || 1
  const offset = Math.min(Math.max((scrollTop - tops[page - 1]) / height, 0), 1)
  return { page, offset }
}

// @doc: docs/design/Reader.md#4-데이터
export function scrollTopFor(page: number, offset: number, tops: number[], heights: number[]): number {
  const index = clampPage(page, tops.length) - 1
  if (tops.length === 0) return 0
  return tops[index] + Math.min(Math.max(offset, 0), 1) * heights[index]
}
