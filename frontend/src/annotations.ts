// @doc: docs/design/Reader.md#6-화면

// @doc: docs/design/Reader.md#4-데이터
export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

// @doc: docs/design/Reader.md#6-화면
export const HIGHLIGHT_COLORS = [
  { name: 'yellow', label: '노랑', fill: 'rgba(250, 204, 21, 0.38)' },
  { name: 'green', label: '초록', fill: 'rgba(74, 222, 128, 0.35)' },
  { name: 'blue', label: '파랑', fill: 'rgba(96, 165, 250, 0.35)' },
  { name: 'pink', label: '분홍', fill: 'rgba(244, 114, 182, 0.35)' },
  { name: 'purple', label: '보라', fill: 'rgba(167, 139, 250, 0.35)' },
] as const

// @doc: docs/design/Reader.md#6-화면
export function colorFill(name: string): string {
  return HIGHLIGHT_COLORS.find((color) => color.name === name)?.fill ?? HIGHLIGHT_COLORS[0].fill
}

interface Box {
  left: number
  top: number
  width: number
  height: number
}

const round = (value: number) => Math.round(value * 100000) / 100000

// @doc: docs/design/Reader.md#4-데이터
export function normalizeRects(rects: Box[], page: Box): Rect[] {
  const inside = rects
    .filter((rect) => rect.width > 0.5 && rect.height > 0.5)
    .map((rect) => ({
      x: (rect.left - page.left) / page.width,
      y: (rect.top - page.top) / page.height,
      w: rect.width / page.width,
      h: rect.height / page.height,
    }))
    .filter((rect) => rect.x < 1 && rect.y < 1 && rect.x + rect.w > 0 && rect.y + rect.h > 0)
    .map((rect) => {
      const x = Math.max(rect.x, 0)
      const y = Math.max(rect.y, 0)
      return { x, y, w: Math.min(rect.x + rect.w, 1) - x, h: Math.min(rect.y + rect.h, 1) - y }
    })
    .sort((a, b) => a.y - b.y || a.x - b.x)
  const merged: Rect[] = []
  for (const rect of inside) {
    const last = merged[merged.length - 1]
    const sameLine = last && Math.abs(rect.y - last.y) < Math.min(rect.h, last.h) * 0.5
    if (last && sameLine && rect.x <= last.x + last.w + 0.02) {
      const right = Math.max(last.x + last.w, rect.x + rect.w)
      const bottom = Math.max(last.y + last.h, rect.y + rect.h)
      last.x = Math.min(last.x, rect.x)
      last.y = Math.min(last.y, rect.y)
      last.w = right - last.x
      last.h = bottom - last.y
    } else {
      merged.push({ ...rect })
    }
  }
  return merged.map((rect) => ({ x: round(rect.x), y: round(rect.y), w: round(rect.w), h: round(rect.h) }))
}

// @doc: docs/design/Reader.md#6-화면
export function hitTest<T extends { page: number; rects: Rect[] }>(
  page: number,
  point: { x: number; y: number },
  annotations: T[],
): T | null {
  for (let index = annotations.length - 1; index >= 0; index -= 1) {
    const annotation = annotations[index]
    if (annotation.page !== page) continue
    const inside = annotation.rects.some(
      (rect) => point.x >= rect.x && point.x <= rect.x + rect.w && point.y >= rect.y && point.y <= rect.y + rect.h,
    )
    if (inside) return annotation
  }
  return null
}

// @doc: docs/design/Reader.md#6-화면
export const MIN_NOTE_SIZE = 0.01

// @doc: docs/design/Reader.md#6-화면
export function dragRect(start: { x: number; y: number }, end: { x: number; y: number }): Rect | null {
  const clamp = (value: number) => Math.min(Math.max(value, 0), 1)
  const x = clamp(Math.min(start.x, end.x))
  const y = clamp(Math.min(start.y, end.y))
  const w = clamp(Math.max(start.x, end.x)) - x
  const h = clamp(Math.max(start.y, end.y)) - y
  if (w < MIN_NOTE_SIZE || h < MIN_NOTE_SIZE) return null
  return { x: round(x), y: round(y), w: round(w), h: round(h) }
}

// @doc: docs/design/Reader.md#6-화면
export function annotationSummary(annotation: { kind: string; text: string | null; note: string | null }): string {
  const parts = annotation.kind === 'highlight' ? [annotation.text, annotation.note] : [annotation.note]
  const summary = parts.filter((part) => part && part.trim()).join(' — ')
  return summary || (annotation.kind === 'highlight' ? '(글 없음)' : '(메모 없음)')
}
