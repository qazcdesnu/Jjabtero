// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
// @doc: docs/design/ReaderCitations.md#3-참고문헌-항목-읽기

import type { Rect } from './annotations'

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export interface CitationLink {
  page: number
  dest: string
  rects: Rect[]
}

// @doc: docs/design/ReaderCitations.md#3-참고문헌-항목-읽기
export interface Anchor {
  name: string
  page: number
  x: number | null
  y: number | null
}

// @doc: docs/design/ReaderCitations.md#3-참고문헌-항목-읽기
export interface TextPiece {
  str: string
  x: number
  y: number
  width?: number
  height?: number
}

// @doc: docs/design/ReaderCitations.md#3-참고문헌-항목-읽기
export const COLUMN_GAP = 50
// @doc: docs/design/ReaderCitations.md#3-참고문헌-항목-읽기
export const ENTRY_MAX_DROP = 80
// @doc: docs/design/ReaderCitations.md#3-참고문헌-항목-읽기
export const ENTRY_MAX_CHARS = 600

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export function isCitationDest(dest: unknown): dest is string {
  return typeof dest === 'string' && dest.startsWith('cite.')
}

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export function linkRect(viewportRect: number[], width: number, height: number): Rect {
  const [x1, y1, x2, y2] = viewportRect
  const left = Math.min(x1, x2)
  const top = Math.min(y1, y2)
  return { x: left / width, y: top / height, w: Math.abs(x2 - x1) / width, h: Math.abs(y2 - y1) / height }
}

// @doc: docs/design/ReaderCitations.md#3-참고문헌-항목-읽기
export function anchorFromDest(name: string, page: number, dest: unknown[]): Anchor {
  const kind = (dest[1] as { name?: string } | undefined)?.name
  if (kind === 'XYZ') {
    const x = typeof dest[2] === 'number' ? dest[2] : null
    const y = typeof dest[3] === 'number' ? dest[3] : null
    return { name, page, x, y }
  }
  if (kind === 'FitH' || kind === 'FitBH') return { name, page, x: null, y: typeof dest[2] === 'number' ? dest[2] : null }
  return { name, page, x: null, y: null }
}

function joinLines(lines: string[]): string {
  let text = ''
  for (const line of lines) {
    const part = line.replace(/\s+/g, ' ').trim()
    if (!part) continue
    // 줄 끝 하이픈으로 끊긴 낱말은 붙인다(다음 줄이 소문자로 시작할 때).
    if (/[A-Za-z]-$/.test(text) && /^[a-z]/.test(part)) text = text.slice(0, -1) + part
    else text = text ? `${text} ${part}` : part
  }
  return text
}

// @doc: docs/design/ReaderCitations.md#3-참고문헌-항목-읽기
export function referenceEntryText(anchor: Anchor, anchors: Anchor[], pieces: TextPiece[], pageRight: number): string {
  if (anchor.y === null) return ''
  const top = anchor.y
  const others = anchors.filter((other) => other.page === anchor.page && other.name !== anchor.name && other.y !== null)
  const left = anchor.x === null ? -Infinity : anchor.x - 10
  const rights = anchor.x === null ? [] : others.flatMap((other) => (other.x !== null && other.x > anchor.x! + COLUMN_GAP ? [other.x] : []))
  const right = Math.min(pageRight, ...rights)
  const sameColumn = others.filter(
    (other) => anchor.x === null || other.x === null || Math.abs(other.x - anchor.x) <= COLUMN_GAP,
  )
  const below = sameColumn.flatMap((other) => (other.y! < top - 1 ? [other.y!] : []))
  const bottom = below.length ? Math.max(...below) : top - ENTRY_MAX_DROP
  const chosen = pieces.filter(
    (piece) => piece.str.trim() && piece.x >= left && piece.x < right - 5 && piece.y <= top + 2 && piece.y > bottom + 2,
  )
  // 기준선이 2pt 안이면 같은 줄로 보고, 위에서 아래, 왼쪽에서 오른쪽으로 잇는다.
  chosen.sort((a, b) => (Math.abs(a.y - b.y) <= 2 ? a.x - b.x : b.y - a.y))
  const lines: string[] = []
  let previous: TextPiece | null = null
  for (const piece of chosen) {
    if (previous === null || Math.abs(piece.y - previous.y) > 2) {
      lines.push(piece.str)
    } else {
      // 같은 줄의 조각 사이가 떨어져 있으면 빈칸을 넣는다. pdf.js 조각에는 빈칸이 빠져 있기도 하다.
      const gap = previous.width === undefined ? 0 : piece.x - (previous.x + previous.width)
      const spaced = /\s$/.test(lines[lines.length - 1]) || /^\s/.test(piece.str)
      lines[lines.length - 1] += (gap > 0.5 && !spaced ? ' ' : '') + piece.str
    }
    previous = piece
  }
  return joinLines(lines).slice(0, ENTRY_MAX_CHARS)
}
