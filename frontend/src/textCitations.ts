// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
// 링크 주석이 없는 PDF에서 글자만으로 참고문헌 항목과 본문 인용 표시를 찾는다.

import type { Rect } from './annotations'

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export interface PageText {
  page: number
  // 쪽의 PDF 좌표 범위 [왼쪽, 아래, 오른쪽, 위]
  view: number[]
  pieces: { str: string; x: number; y: number; width: number; height: number }[]
}

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export interface TextLine {
  page: number
  x: number
  y: number
  height: number
  text: string
}

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export interface ReferenceEntry {
  number: number | null
  surname: string
  years: string[]
  text: string
  page: number
  y: number
  // 항목 마지막 줄의 쪽과 기준선
  endPage: number
  bottom: number
}

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export interface TextMarker {
  entry: number
  rects: Rect[]
}

const HEADING = /^(?:\d+\.?\s*)?(?:references|bibliography|참고\s*문헌)$/i
// 참고문헌 뒤에 오는 부록 제목. "A survey of …" 같은 항목 줄과 헷갈리지 않게, 낱말이나 모두 대문자인 절 제목만 본다.
const STOP_WORD = /^(?:[A-Z]\.?\s+)?(?:appendix|appendices|supplementary)\b/i
const STOP_CAPS = /^[A-Z](?:\.\d+)*\s+[A-Z][A-Z\s:,-]{3,}$/
const NUMBERED = /^\s*(?:\[(\d{1,4})\]|(\d{1,4})\.\s)/
// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
// 번호 양식에서 다음 항목 번호는 앞 번호보다 크고 이만큼 안이다. "2025. URL …"처럼 연도로 시작하는 이어지는 줄을 항목으로 보지 않기 위해서다.
export const NUMBER_STEP = 3
const YEAR = /(?:19|20)\d{2}/g
// 같은 줄에서 이만큼(pt) 넘게 떨어진 조각은 다른 단으로 본다.
const COLUMN_GAP = 40

function normalizeName(text: string): string {
  return text
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
}

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export function pageLines(page: PageText): TextLine[] {
  const pieces = page.pieces.filter((piece) => piece.str.trim())
  pieces.sort((a, b) => (Math.abs(a.y - b.y) <= 2 ? a.x - b.x : b.y - a.y))
  const lines: (TextLine & { end: number })[] = []
  for (const piece of pieces) {
    const last = lines[lines.length - 1]
    if (last && Math.abs(last.y - piece.y) <= 2 && piece.x - last.end < COLUMN_GAP) {
      const gap = piece.x - last.end
      last.text += (gap > 0.5 && !/\s$/.test(last.text) && !/^\s/.test(piece.str) ? ' ' : '') + piece.str
      last.end = Math.max(last.end, piece.x + piece.width)
      last.height = Math.max(last.height, piece.height)
    } else {
      lines.push({ page: page.page, x: piece.x, y: piece.y, height: piece.height, text: piece.str, end: piece.x + piece.width })
    }
  }
  return lines.map(({ end: _end, ...line }) => ({ ...line, text: line.text.replace(/\s+/g, ' ').trim() }))
}

// 위아래 끝 6% 안의 줄(머리말, 꼬리말, 쪽 번호)은 뺀다.
function bodyLines(page: PageText): TextLine[] {
  const [, bottom, , top] = page.view
  const margin = (top - bottom) * 0.06
  return pageLines(page).filter((line) => line.y > bottom + margin && line.y < top - margin && !/^\d+$/.test(line.text))
}

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export function hasReferenceHeading(page: PageText): boolean {
  return bodyLines(page).some(isHeading)
}

function isHeading(line: TextLine): boolean {
  // 작은 대문자 제목은 "R" "EFERENCES"처럼 조각나 있어 빈칸을 빼고 본다.
  return HEADING.test(line.text) || HEADING.test(line.text.replace(/\s+/g, ''))
}

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export function firstSurname(text: string): string {
  const body = text.replace(NUMBERED, '').trim()
  const head = body.split(/,|\.\s|\s(?:and|&)\s/)[0].trim()
  const words = head.split(/\s+/).filter(Boolean)
  // "Bahdanau, D." 처럼 성이 먼저 오면 쉼표 앞 한 낱말, "Dzmitry Bahdanau" 처럼 이름이 먼저 오면 마지막 낱말이다.
  const surname = body.indexOf(',') === head.length && words.length === 1 ? words[0] : words[words.length - 1] ?? ''
  return normalizeName(surname.replace(/[^\p{L}'’-]/gu, ''))
}

// 여러 쪽의 같은 높이에 같은 글(숫자는 무시)이 되풀이되는 줄은 머리말·꼬리말이다. 학술지가 덧붙인 머리말은
// 위 6%보다 안쪽에 있기도 해서, 참고문헌 목록이 그 줄에서 끝난 것으로 잘못 보았다(이슈 H4).
function dropRunningLines(lines: TextLine[]): TextLine[] {
  const key = (line: TextLine) => `${Math.round(line.y)}|${line.text.replace(/\d+/g, '#')}`
  const pagesByKey = new Map<string, Set<number>>()
  for (const line of lines) {
    const pages = pagesByKey.get(key(line)) ?? new Set<number>()
    pages.add(line.page)
    pagesByKey.set(key(line), pages)
  }
  return lines.filter((line) => (pagesByKey.get(key(line))?.size ?? 0) < 2)
}

function entryNumber(match: RegExpExecArray | null, bracket: boolean): number | null {
  if (!match) return null
  const value = bracket ? match[1] : match[2]
  return value === undefined ? null : Number(value)
}

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export function referenceEntries(pages: PageText[]): ReferenceEntry[] {
  const lines = dropRunningLines(pages.flatMap(bodyLines))
  let start = -1
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    if (isHeading(lines[index])) {
      start = index
      break
    }
  }
  if (start < 0) return []
  const body: TextLine[] = []
  for (const line of lines.slice(start + 1)) {
    if ((STOP_WORD.test(line.text) || STOP_CAPS.test(line.text)) && line.text.length < 60) break
    body.push(line)
  }
  const numbered = body.filter((line) => NUMBERED.test(line.text)).length >= Math.min(3, body.length)
  // `[n]`과 `n.` 가운데 많은 쪽만 항목 번호로 본다.
  const brackets = body.filter((line) => NUMBERED.exec(line.text)?.[1] !== undefined).length
  const bracket = brackets * 2 >= body.filter((line) => NUMBERED.test(line.text)).length
  // 두 단이면 쪽마다 왼쪽 단을 다 읽고 오른쪽 단을 읽는다. 왼쪽 끝에서 150pt 넘게 오른쪽이면 오른쪽 단이다.
  const lefts = new Map<number, number>()
  for (const line of body) lefts.set(line.page, Math.min(lefts.get(line.page) ?? Infinity, line.x))
  const right = (line: TextLine) => line.x > (lefts.get(line.page) ?? line.x) + 150
  // 오른쪽에 있는 줄이 쪽 줄의 1/4 이상일 때만 두 단으로 본다. 한 단 쪽에서 낱말 사이가 크게 벌어져 줄의 뒷부분이
  // 따로 떨어진 것을 오른쪽 단으로 보면 목록이 거기서 끝나 버린다(이슈 H4).
  const twoColumns = new Set(
    [...lefts.keys()].filter((page) => {
      const onPage = body.filter((line) => line.page === page)
      return onPage.filter(right).length * 4 >= onPage.length
    }),
  )
  const side = (line: TextLine) => (twoColumns.has(line.page) && right(line) ? 1 : 0)
  body.sort((a, b) => a.page - b.page || side(a) - side(b) || (Math.abs(a.y - b.y) <= 2 ? a.x - b.x : b.y - a.y))
  // 내어쓰기 양식: 쪽·단마다 가장 왼쪽 줄이 항목의 첫 줄이다.
  const margins = new Map<string, number>()
  for (const line of body) {
    const key = `${line.page}:${side(line)}`
    margins.set(key, Math.min(margins.get(key) ?? Infinity, line.x))
  }
  const entries: ReferenceEntry[] = []
  for (const line of body) {
    const margin = margins.get(`${line.page}:${side(line)}`) ?? line.x
    const match = NUMBERED.exec(line.text)
    const last = entries[entries.length - 1]
    const number = numbered ? entryNumber(match, bracket) : null
    const previous = last?.number ?? 0
    const starts = numbered ? number !== null && number > previous && number <= previous + NUMBER_STEP : line.x <= margin + 1.5
    if (!starts && last) {
      // 항목이 끝난 뒤의 글(그림 부록 등)을 끌어오지 않는다. 번호 양식의 이어지는 줄은 들여쓰여 있고,
      // 같은 쪽에서 줄 사이가 크게 벌어지면 목록이 끝난 것이다.
      const unindented = numbered && line.x <= margin + 1.5
      const farBelow = line.page === last.endPage && last.bottom - line.y > Math.max(line.height, 8) * 3.5
      if (unindented || farBelow) break
    }
    if (starts || !last) {
      entries.push({
        number,
        surname: '',
        years: [],
        text: line.text,
        page: line.page,
        y: line.y + line.height,
        endPage: line.page,
        bottom: line.y,
      })
      continue
    } else if (/[A-Za-z]-$/.test(last.text) && /^[a-z]/.test(line.text)) {
      last.text = last.text.slice(0, -1) + line.text
    } else {
      last.text = `${last.text} ${line.text}`
    }
    if (line.page !== last.endPage) {
      last.endPage = line.page
      last.bottom = line.y
    } else {
      last.bottom = Math.min(last.bottom, line.y)
    }
  }
  for (const entry of entries) {
    entry.surname = firstSurname(entry.text)
    entry.years = [...new Set(entry.text.match(YEAR) ?? [])]
  }
  return entries
}

function rectFor(page: PageText, piece: PageText['pieces'][number], start: number, end: number): Rect {
  const [left, bottom, right, top] = page.view
  const length = Math.max(piece.str.length, 1)
  const x0 = piece.x + (piece.width * start) / length
  const x1 = piece.x + (piece.width * end) / length
  const height = piece.height || 10
  const y1 = piece.y + height * 0.85
  const y0 = piece.y - height * 0.25
  return {
    x: (x0 - left) / (right - left),
    y: (top - y1) / (top - bottom),
    w: (x1 - x0) / (right - left),
    h: (y1 - y0) / (top - bottom),
  }
}

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export function authorYearEntry(entries: ReferenceEntry[], surname: string, year: string, letter = ''): number {
  const name = normalizeName(surname)
  const same = entries.flatMap((entry, index) => (entry.surname === name && entry.years.includes(year) ? [index] : []))
  if (same.length === 0) return -1
  if (letter) {
    const exact = same.find((index) => entries[index].text.includes(`${year}${letter}`))
    if (exact !== undefined) return exact
    // 2025a, 2025b는 참고문헌에 나온 순서다.
    return same[letter.charCodeAt(0) - 97] ?? -1
  }
  return same[0]
}

const NUMERIC_MARKER = /\[(\d{1,4}(?:\s*[,–-]\s*\d{1,4})*)\]/g
const AUTHOR_YEAR = /(\p{Lu}[\p{L}'’-]+)(?:\s+et\s+al\.?|\s+(?:and|&)\s+\p{Lu}[\p{L}'’-]+)?,?\s*\(?((?:19|20)\d{2})([a-z])?/gu

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export function inReferences(page: number, y: number, entries: ReferenceEntry[]): boolean {
  if (entries.length === 0) return false
  const first = entries[0]
  const last = entries[entries.length - 1]
  const afterStart = page > first.page || (page === first.page && y <= first.y + 1)
  const beforeEnd = page < last.endPage || (page === last.endPage && y >= last.bottom - 1)
  return afterStart && beforeEnd
}

// @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기
export function findMarkers(page: PageText, entries: ReferenceEntry[]): TextMarker[] {
  if (entries.length === 0) return []
  const numbered = entries.some((entry) => entry.number !== null)
  const byNumber = new Map(entries.flatMap((entry, index) => (entry.number === null ? [] : [[entry.number, index] as const])))
  const markers: TextMarker[] = []
  for (const piece of page.pieces) {
    // 참고문헌 목록 안의 "[5]" 같은 항목 번호는 인용 표시가 아니다.
    if (inReferences(page.page, piece.y, entries)) continue
    if (numbered) {
      for (const match of piece.str.matchAll(NUMERIC_MARKER)) {
        const inside = match.index! + 1
        for (const number of match[1].matchAll(/\d{1,4}/g)) {
          const entry = byNumber.get(Number(number[0]))
          if (entry === undefined) continue
          const start = inside + number.index!
          markers.push({ entry, rects: [rectFor(page, piece, start, start + number[0].length)] })
        }
      }
    } else {
      for (const match of piece.str.matchAll(AUTHOR_YEAR)) {
        const entry = authorYearEntry(entries, match[1], match[2], match[3] ?? '')
        if (entry < 0) continue
        markers.push({ entry, rects: [rectFor(page, piece, match.index!, match.index! + match[0].length)] })
      }
    }
  }
  return markers
}
