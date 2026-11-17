// @doc: docs/design/ReaderCitations.md#6-테스트

import { describe, expect, it } from 'vitest'
import {
  authorYearEntry,
  findMarkers,
  firstSurname,
  hasReferenceHeading,
  inReferences,
  pageLines,
  referenceEntries,
  type PageText,
} from './textCitations'

const VIEW = [0, 0, 612, 792]

// 줄마다 [x, y, 글]로 쪽을 만든다. 글자 하나의 너비는 5pt다.
function page(number: number, lines: [number, number, string][]): PageText {
  return { page: number, view: VIEW, pieces: lines.map(([x, y, str]) => ({ str, x, y, width: str.length * 5, height: 10 })) }
}

const numbered = [
  page(1, [
    [100, 700, 'Recurrent models [2] and attention [1, 3] are used.'],
    [100, 680, 'See also [9] which is not a reference.'],
  ]),
  page(2, [
    [100, 700, 'References'],
    [108, 680, '[1] Jimmy Lei Ba, Jamie Kiros, and Geoffrey Hinton. Layer normaliza-'],
    [124, 668, 'tion. arXiv preprint, 2016.'],
    [108, 650, '[2] Dzmitry Bahdanau and Yoshua Bengio. Neural machine translation. 2014.'],
    [108, 630, '[3] Kyunghyun Cho. Learning phrase representations. 2014.'],
    [100, 500, 'Attention Visualizations'],
    [100, 480, 'Figure 3: An example of the attention mechanism.'],
  ]),
]

const authorYear = [
  page(1, [[100, 700, 'evolution (Darwin, 2023) and (Zhang et al., 2025b; Zhang et al., 2025a) and Unknown, 2020.']]),
  page(2, [
    [100, 700, 'R EFERENCES'],
    [108, 680, 'Charles Darwin. Origin of the species. Routledge, 2023.'],
    [108, 660, 'Jenny Zhang, Shengran Hu, and Jeff Clune. Omni: Open-endedness via models of'],
    [118, 648, 'human notions of interestingness. 2025.'],
    [108, 630, 'Jenny Zhang, Shengran Hu, Cong Lu, and Jeff Clune. Darwin godel machine. 2025.'],
    [100, 400, 'A APPENDIX'],
    [108, 380, 'Some appendix text that is not a reference, 2024.'],
  ]),
]

describe('pageLines', () => {
  it('같은 줄 조각을 잇고, 멀리 떨어진 조각(다른 단)은 나누며, 위에서 아래로 둔다', () => {
    const lines = pageLines({
      page: 1,
      view: VIEW,
      pieces: [
        { str: 'world', x: 131, y: 700, width: 25, height: 10 },
        { str: 'hello', x: 100, y: 700, width: 25, height: 10 },
        { str: 'right column', x: 330, y: 700, width: 60, height: 10 },
        { str: 'below', x: 100, y: 680, width: 25, height: 10 },
      ],
    })
    expect(lines.map((line) => line.text)).toEqual(['hello world', 'right column', 'below'])
  })
})

describe('referenceEntries', () => {
  it('번호 양식은 [n]으로 항목을 나누고, 줄 끝 하이픈을 붙이며, 들여쓰지 않은 줄에서 끝난다', () => {
    const entries = referenceEntries(numbered)
    expect(entries.map((entry) => [entry.number, entry.surname, entry.years])).toEqual([
      [1, 'ba', ['2016']],
      [2, 'bahdanau', ['2014']],
      [3, 'cho', ['2014']],
    ])
    expect(entries[0].text).toBe('[1] Jimmy Lei Ba, Jamie Kiros, and Geoffrey Hinton. Layer normalization. arXiv preprint, 2016.')
  })

  it('내어쓰기 양식은 가장 왼쪽 줄로 항목을 나누고, 조각난 작은 대문자 제목을 알아보며, 부록 제목에서 끝난다', () => {
    const entries = referenceEntries(authorYear)
    expect(entries.map((entry) => [entry.number, entry.surname])).toEqual([
      [null, 'darwin'],
      [null, 'zhang'],
      [null, 'zhang'],
    ])
    expect(entries[1].text).toContain('models of human notions')
    expect(hasReferenceHeading(authorYear[1])).toBe(true)
    expect(hasReferenceHeading(authorYear[0])).toBe(false)
  })

  it('학술지 머리말, 낱말 사이가 크게 벌어진 줄, 연도로 시작하는 이어지는 줄에서 목록을 끊지 않는다', () => {
    const view = [0, 0, 612, 792]
    const header = (page: number) => [
      { str: 'Journal of Things – Safety', x: 72, y: 758, width: 150, height: 10 },
      { str: `2025 ${page}(3) Agents`, x: 328, y: 758, width: 120, height: 10 },
    ]
    const piece = (str: string, x: number, y: number) => ({ str, x, y, width: str.length * 4.5, height: 10 })
    const pages: PageText[] = [
      {
        page: 1,
        view,
        pieces: [
          ...header(1),
          piece('References', 108, 720),
          piece('[1] Ann Lee. A first paper. Venue,', 113, 700),
          piece('2025. URL https://example.org/a.', 134, 689),
          piece('[2] Bo Kim. Gemini model', 113, 678),
          piece('updates — march 2025.', 300, 678),
          piece('[3] Cy Park. Third. 2024.', 113, 667),
        ],
      },
      {
        page: 2,
        view,
        pieces: [...header(2), piece('[4] Di Choi. Fourth. 2023.', 113, 710), piece('[5] Ed Han. Fifth. 2022.', 113, 699)],
      },
    ]
    const entries = referenceEntries(pages)
    expect(entries.map((entry) => entry.number)).toEqual([1, 2, 3, 4, 5])
    expect(entries[0].text).toBe('[1] Ann Lee. A first paper. Venue, 2025. URL https://example.org/a.')
    expect(entries[1].text).toBe('[2] Bo Kim. Gemini model updates — march 2025.')
  })

  it('참고문헌 제목이 없으면 빈 목록이다', () => {
    expect(referenceEntries([numbered[0]])).toEqual([])
  })
})

describe('이름과 연도', () => {
  it('첫 저자의 성을 고른다', () => {
    expect(firstSurname('[2] Dzmitry Bahdanau, Kyunghyun Cho. Title.')).toBe('bahdanau')
    expect(firstSurname('Bahdanau, D., Cho, K. (2014). Title.')).toBe('bahdanau')
    expect(firstSurname('N Bostrom. Existential risks. 2002.')).toBe('bostrom')
    expect(firstSurname('Jürgen Schmidhuber. Gödel machines. 2003.')).toBe('schmidhuber')
  })

  it('같은 성·연도는 글자(a, b)로 고르고, 글자가 없으면 참고문헌 순서다', () => {
    const entries = referenceEntries(authorYear)
    expect(authorYearEntry(entries, 'Zhang', '2025', 'a')).toBe(1)
    expect(authorYearEntry(entries, 'Zhang', '2025', 'b')).toBe(2)
    expect(authorYearEntry(entries, 'Darwin', '2023')).toBe(0)
    expect(authorYearEntry(entries, 'Darwin', '1859')).toBe(-1)
  })
})

describe('findMarkers', () => {
  it('번호 양식은 대괄호 안 숫자마다 항목과 잇고, 없는 번호와 참고문헌 목록 안은 건너뛴다', () => {
    const entries = referenceEntries(numbered)
    const markers = findMarkers(numbered[0], entries)
    expect(markers.map((marker) => entries[marker.entry].number)).toEqual([2, 1, 3])
    const [first] = markers
    // "[2]"의 "2"는 "Recurrent models [" 다음(18번째 글자)이다.
    expect(first.rects[0].x).toBeCloseTo((100 + 18 * 5) / 612)
    expect(first.rects[0].w).toBeCloseTo(5 / 612)
    expect(findMarkers(numbered[1], entries)).toEqual([])
    expect(inReferences(2, 650, entries)).toBe(true)
    expect(inReferences(1, 700, entries)).toBe(false)
  })

  it('저자-연도 양식은 성과 연도(글자 포함)로 항목과 잇고, 참고문헌에 없는 이름은 건너뛴다', () => {
    const entries = referenceEntries(authorYear)
    const markers = findMarkers(authorYear[0], entries)
    expect(markers.map((marker) => entries[marker.entry].text.slice(0, 30))).toEqual([
      'Charles Darwin. Origin of the ',
      'Jenny Zhang, Shengran Hu, Cong',
      'Jenny Zhang, Shengran Hu, and ',
    ])
  })
})
