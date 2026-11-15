// @doc: docs/design/CitationStyles.md#2-양식

import type { PaperInput } from './api'

// @doc: docs/design/CitationStyles.md#1-범위
export type CitableWork = Pick<PaperInput, 'title' | 'authors' | 'item_type' | 'year' | 'venue' | 'doi' | 'url'>

// @doc: docs/design/CitationStyles.md#2-양식
export interface FormattedCitation {
  text: string
  html: string
  latex: string
}

// @doc: docs/design/CitationStyles.md#5-복사
export type CopyMode = 'document' | 'latex'

const LATEX_SPECIALS: Record<string, string> = {
  '\\': '\\textbackslash{}',
  '&': '\\&',
  '%': '\\%',
  '$': '\\$',
  '#': '\\#',
  '_': '\\_',
  '{': '\\{',
  '}': '\\}',
  '~': '\\textasciitilde{}',
  '^': '\\textasciicircum{}',
}

// @doc: docs/design/CitationStyles.md#5-복사
export function escapeLatex(text: string): string {
  return text.replace(/[\\&%$#_{}~^]/g, (char) => LATEX_SPECIALS[char])
}

// @doc: docs/design/CitationStyles.md#3-저자-이름
export interface PersonName {
  given: string
  family: string
}

const PARTICLES = new Set(['van', 'von', 'de', 'der', 'den', 'di', 'da', 'del', 'della', 'du', 'le', 'la', 'dos', 'das', 'ten', 'ter'])
const SUFFIXES = new Set(['jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv'])
const ARXIV_DOI = /^10\.48550\/arxiv\.(.+)$/i

// @doc: docs/design/CitationStyles.md#3-저자-이름
export function splitName(raw: string): PersonName {
  const name = raw.replace(/\s+/g, ' ').trim()
  if (name.includes(',')) {
    const [family, ...rest] = name.split(',')
    return { family: family.trim(), given: rest.join(',').trim() }
  }
  const words = name.split(' ')
  if (words.length === 1) return { given: '', family: words[0] }
  let end = words.length
  if (end > 2 && SUFFIXES.has(words[end - 1].toLowerCase())) end -= 1
  let start = end - 1
  while (start > 1 && PARTICLES.has(words[start - 1].toLowerCase())) start -= 1
  const family = [...words.slice(start, end), ...words.slice(end)].join(' ')
  return { given: words.slice(0, start).join(' '), family }
}

// @doc: docs/design/CitationStyles.md#3-저자-이름
export function initials(given: string, withPeriods = true): string {
  const parts = given.split(/[\s.]+/).filter(Boolean)
  return parts
    .map((part) =>
      part
        .split('-')
        .map((piece) => (piece ? piece[0].toUpperCase() + (withPeriods ? '.' : '') : ''))
        .join(withPeriods ? '-' : ''),
    )
    .join(withPeriods ? ' ' : '')
}

function escapeHtml(text: string): string {
  return text.replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[char]!)
}

// 글 조각을 이어 일반 글, HTML, LaTeX를 함께 만든다.
// 기울일 조각은 `italic`, 주소는 `url`, 따옴표로 감쌀 조각은 `quote`(작은따옴표면 `single`)로 표시한다.
type Piece = string | { italic: string } | { url: string } | { quote: string; single?: boolean }

function build(pieces: Piece[]): FormattedCitation {
  let text = ''
  let html = ''
  let latex = ''
  for (const piece of pieces) {
    if (typeof piece === 'string') {
      text += piece
      html += escapeHtml(piece)
      latex += escapeLatex(piece)
    } else if ('italic' in piece) {
      if (!piece.italic) continue
      text += piece.italic
      html += `<i>${escapeHtml(piece.italic)}</i>`
      latex += `\\textit{${escapeLatex(piece.italic)}}`
    } else if ('url' in piece) {
      if (!piece.url) continue
      text += piece.url
      html += escapeHtml(piece.url)
      latex += `\\url{${piece.url.replace(/[{}\\]/g, '')}}`
    } else {
      const [open, close, texOpen, texClose] = piece.single ? ["'", "'", '`', "'"] : ['"', '"', '``', "''"]
      text += `${open}${piece.quote}${close}`
      html += escapeHtml(`${open}${piece.quote}${close}`)
      latex += `${texOpen}${escapeLatex(piece.quote)}${texClose}`
    }
  }
  const tidy = (value: string) => value.replace(/\s+/g, ' ').trim()
  return { text: tidy(text), html: tidy(html), latex: tidy(latex) }
}

function joinList(items: string[], conjunction: string, serialComma = true): string {
  if (items.length <= 1) return items.join('')
  if (items.length === 2) return `${items[0]} ${conjunction} ${items[1]}`
  return `${items.slice(0, -1).join(', ')}${serialComma ? ',' : ''} ${conjunction} ${items[items.length - 1]}`
}

function endWith(text: string, mark = '.'): string {
  return /[.?!]$/.test(text) ? text : `${text}${mark}`
}

// @doc: docs/design/CitationStyles.md#2-양식
export function arxivId(work: CitableWork): string | null {
  const match = ARXIV_DOI.exec(work.doi ?? '')
  return match ? match[1] : null
}

function link(work: CitableWork): Piece {
  if (work.doi) return { url: `https://doi.org/${work.doi}` }
  return work.url ? { url: work.url } : ''
}

function hasLink(work: CitableWork): boolean {
  return Boolean(work.doi || work.url)
}

// OpenAlex는 arXiv 논문의 게재처를 "arXiv (Cornell University)"처럼 준다. 이런 게재처는 없는 것으로 본다.
// @doc: docs/design/CitationStyles.md#2-양식
export function publishedVenue(work: CitableWork): string | null {
  return work.venue && !/^arxiv\b/i.test(work.venue.trim()) ? work.venue : null
}

// 게재처 이름. 게재처가 없는 arXiv 논문은 "arXiv preprint arXiv:<ID>"로 쓴다.
function venueOf(work: CitableWork): string {
  const venue = publishedVenue(work)
  if (venue) return venue
  const arxiv = arxivId(work)
  return arxiv ? `arXiv preprint arXiv:${arxiv}` : (work.venue ?? '')
}

function isProceedings(work: CitableWork): boolean {
  return work.item_type === 'conference-paper' || work.item_type === 'book-chapter'
}

function names(work: CitableWork): PersonName[] {
  return work.authors.map(splitName)
}

function full(name: PersonName): string {
  return [name.given, name.family].filter(Boolean).join(' ')
}

function inverted(name: PersonName): string {
  return name.given ? `${name.family}, ${name.given}` : name.family
}

// @doc: docs/design/CitationStyles.md#2-양식
export function apa(work: CitableWork): FormattedCitation {
  const people = names(work).map((name) => (name.given ? `${name.family}, ${initials(name.given)}` : name.family))
  let authors = ''
  if (people.length > 20) authors = `${people.slice(0, 19).join(', ')}, . . . ${people[people.length - 1]}`
  else authors = people.length > 1 ? `${people.slice(0, -1).join(', ')}, & ${people[people.length - 1]}` : (people[0] ?? '')
  const venue = venueOf(work)
  return build([
    authors ? `${endWith(authors)} ` : '',
    `(${work.year ?? 'n.d.'}). `,
    `${endWith(work.title)} `,
    venue ? { italic: venue } : '',
    venue ? '. ' : '',
    link(work),
  ])
}

// @doc: docs/design/CitationStyles.md#2-양식
export function mla(work: CitableWork): FormattedCitation {
  const people = names(work)
  let authors = ''
  if (people.length === 1) authors = inverted(people[0])
  else if (people.length === 2) authors = `${inverted(people[0])}, and ${full(people[1])}`
  else if (people.length > 2) authors = `${inverted(people[0])}, et al`
  const venue = venueOf(work)
  const year = work.year ? String(work.year) : ''
  const tail = Boolean(year || hasLink(work))
  return build([
    authors ? `${endWith(authors)} ` : '',
    { quote: endWith(work.title) },
    ' ',
    venue ? { italic: venue } : '',
    venue && tail ? ', ' : venue ? '.' : '',
    year,
    year && hasLink(work) ? ', ' : '',
    link(work),
    tail ? '.' : '',
  ])
}

// @doc: docs/design/CitationStyles.md#2-양식
export function chicago(work: CitableWork): FormattedCitation {
  const people = names(work)
  const listed = people.length > 10 ? people.slice(0, 7) : people
  const parts = listed.map((name, index) => (index === 0 ? inverted(name) : full(name)))
  // 첫 저자는 이름을 뒤집으므로 둘뿐이어도 "and" 앞에 쉼표를 둔다.
  let authors = parts.length === 2 ? `${parts[0]}, and ${parts[1]}` : joinList(parts, 'and')
  if (people.length > 10) authors = `${parts.join(', ')}, et al`
  const venue = venueOf(work)
  return build([
    authors ? `${endWith(authors)} ` : '',
    { quote: endWith(work.title) },
    ' ',
    venue ? { italic: venue } : '',
    work.year ? ` (${work.year})` : '',
    venue || work.year ? '. ' : '',
    link(work),
  ])
}

// @doc: docs/design/CitationStyles.md#2-양식
export function harvard(work: CitableWork): FormattedCitation {
  const people = names(work).map((name) => (name.given ? `${name.family}, ${initials(name.given)}` : name.family))
  const authors = people.length > 3 ? `${people[0]} et al.` : joinList(people, 'and', false)
  const venue = venueOf(work)
  return build([
    authors ? `${authors} ` : '',
    `(${work.year ?? 'n.d.'}) `,
    { quote: work.title, single: true },
    venue ? ', ' : '. ',
    venue ? { italic: venue } : '',
    venue ? '. ' : '',
    hasLink(work) ? 'Available at: ' : '',
    link(work),
    hasLink(work) ? '.' : '',
  ])
}

// @doc: docs/design/CitationStyles.md#2-양식
export function vancouver(work: CitableWork): FormattedCitation {
  const people = names(work).map((name) => [name.family, initials(name.given, false)].filter(Boolean).join(' '))
  const authors = people.length > 6 ? `${people.slice(0, 6).join(', ')}, et al.` : people.join(', ')
  const venue = venueOf(work)
  return build([
    authors ? `${endWith(authors)} ` : '',
    `${endWith(work.title)} `,
    venue ? `${endWith(venue)} ` : '',
    work.year ? `${work.year}. ` : '',
    work.doi ? `doi:${work.doi}` : work.url ? { url: work.url } : '',
  ])
}

// @doc: docs/design/CitationStyles.md#2-양식
export function ieee(work: CitableWork): FormattedCitation {
  const people = names(work).map((name) => [initials(name.given), name.family].filter(Boolean).join(' '))
  const venue = venueOf(work)
  const pieces: Piece[] = []
  if (people.length > 6) pieces.push(`${people[0]} `, { italic: 'et al.' }, ', ')
  else if (people.length) pieces.push(`${joinList(people, 'and')}, `)
  pieces.push({ quote: `${work.title},` }, ' ')
  const arxiv = arxivId(work)
  const placed = Boolean((!publishedVenue(work) && arxiv) || venue)
  if (!publishedVenue(work) && arxiv) pieces.push(`arXiv:${arxiv}`)
  else if (venue) pieces.push(isProceedings(work) ? 'in ' : '', { italic: venue })
  if (work.year) pieces.push(`${placed ? ', ' : ''}${work.year}`)
  if (work.doi && !arxiv) pieces.push(`, doi: ${work.doi}`)
  pieces.push('.')
  return build(pieces)
}

// @doc: docs/design/CitationStyles.md#2-양식
export function acm(work: CitableWork): FormattedCitation {
  const authors = joinList(names(work).map(full), 'and')
  const venue = venueOf(work)
  return build([
    authors ? `${endWith(authors)} ` : '',
    work.year ? `${work.year}. ` : '',
    `${endWith(work.title)} `,
    venue && isProceedings(work) ? 'In ' : '',
    venue ? { italic: venue } : '',
    venue ? '. ' : '',
    link(work),
  ])
}

// @doc: docs/design/CitationStyles.md#4-bibtex
export function bibtexKey(work: CitableWork): string {
  const family = work.authors.length ? splitName(work.authors[0]).family : 'anon'
  const word = work.title
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .find((part) => part.length > 3 && !['with', 'from', 'that', 'this', 'into', 'over'].includes(part))
  const plain = (text: string) => text.normalize('NFKD').replace(/[^A-Za-z0-9]/g, '').toLowerCase()
  return `${plain(family) || 'anon'}${work.year ?? ''}${word ?? ''}`
}

const BIBTEX_TYPES: Record<string, [string, string]> = {
  'journal-article': ['article', 'journal'],
  'conference-paper': ['inproceedings', 'booktitle'],
  'book-chapter': ['incollection', 'booktitle'],
  book: ['book', 'publisher'],
  thesis: ['phdthesis', 'school'],
  report: ['techreport', 'institution'],
}

// @doc: docs/design/CitationStyles.md#4-bibtex
export function bibtex(work: CitableWork): FormattedCitation {
  const arxiv = arxivId(work)
  const preprint = Boolean(arxiv && !publishedVenue(work))
  const [type, venueField] = BIBTEX_TYPES[work.item_type] ?? [preprint ? 'article' : 'misc', preprint ? 'journal' : 'howpublished']
  const value = (text: string) => text.replace(/[{}]/g, '')
  const fields: [string, string][] = [
    ['title', `{${value(work.title)}}`],
    ['author', value(work.authors.map((author) => inverted(splitName(author))).join(' and '))],
  ]
  const venue = venueOf(work)
  if (venue) fields.push([venueField, value(venue)])
  if (work.year) fields.push(['year', String(work.year)])
  if (arxiv) fields.push(['eprint', arxiv], ['archivePrefix', 'arXiv'])
  if (work.doi) fields.push(['doi', work.doi])
  else if (work.url) fields.push(['url', work.url])
  const body = fields.filter(([, field]) => field).map(([name, field]) => `  ${name} = {${field}}`).join(',\n')
  const text = `@${type}{${bibtexKey(work)},\n${body}\n}`
  // BibTeX는 서식 없이 글로만 복사한다. LaTeX 모드에서도 그대로 .bib 파일에 붙여 넣는다.
  return { text, html: '', latex: text }
}

// @doc: docs/design/CitationStyles.md#2-양식
export const CITATION_STYLES = [
  { id: 'bibtex', label: 'BibTeX', format: bibtex },
  { id: 'ieee', label: 'IEEE', format: ieee },
  { id: 'acm', label: 'ACM', format: acm },
  { id: 'apa', label: 'APA', format: apa },
  { id: 'mla', label: 'MLA', format: mla },
  { id: 'chicago', label: 'Chicago', format: chicago },
  { id: 'harvard', label: 'Harvard', format: harvard },
  { id: 'vancouver', label: 'Vancouver', format: vancouver },
] as const

// @doc: docs/design/CitationStyles.md#5-복사
export async function copyCitation(
  citation: FormattedCitation,
  mode: CopyMode = 'document',
  clipboard: Clipboard = navigator.clipboard,
): Promise<void> {
  if (mode === 'latex') {
    await clipboard.writeText(citation.latex)
    return
  }
  // 기울임이 붙여 넣는 곳에 남도록 HTML도 함께 복사한다. 지원하지 않으면 글만 복사한다.
  if (citation.html && typeof ClipboardItem !== 'undefined' && clipboard.write) {
    try {
      await clipboard.write([
        new ClipboardItem({
          'text/plain': new Blob([citation.text], { type: 'text/plain' }),
          'text/html': new Blob([citation.html], { type: 'text/html' }),
        }),
      ])
      return
    } catch {
      // 글만 복사한다.
    }
  }
  await clipboard.writeText(citation.text)
}
