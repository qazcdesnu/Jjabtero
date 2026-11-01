// @doc: docs/design/LibraryFilter.md#5-테스트
// @doc: docs/design/ReadingStatus.md#4-테스트

import { describe, expect, it } from 'vitest'
import type { Paper } from './api'
import { emptyFilter, filterPapers, isFilterActive, tagCounts } from './libraryFilter'

function paper(id: number, fields: Partial<Paper>): Paper {
  return {
    id,
    title: `Paper ${id}`,
    authors: [],
    item_type: 'other',
    year: null,
    venue: null,
    doi: null,
    url: null,
    tags: [],
    read_status: 'to-read',
    note: null,
    created_at: '2026-11-01T00:00:00',
    updated_at: '2026-11-01T00:00:00',
    ...fields,
  }
}

const papers = [
  paper(1, { title: 'Graph Neural Networks', authors: ['Kim'], year: 2019, item_type: 'journal-article', tags: ['gnn', 'survey'] }),
  paper(2, { title: 'Attention', authors: ['Vaswani'], year: 2017, item_type: 'preprint', venue: 'arXiv', tags: ['nlp'], read_status: 'read' }),
  paper(3, { title: 'Social Recommendation', authors: ['Fan'], year: 2021, item_type: 'conference-paper', doi: '10.1145/abc', tags: ['gnn'], read_status: 'reading' }),
  paper(4, { title: 'No Year', item_type: 'report' }),
]

const ids = (list: Paper[]) => list.map((item) => item.id)

describe('filterPapers', () => {
  it('빈 조건이면 모두 순서대로 돌려준다', () => {
    expect(ids(filterPapers(papers, emptyFilter()))).toEqual([1, 2, 3, 4])
  })

  it('글자는 낱말을 모두, 대소문자 없이 제목·저자·게재처·DOI·태그에서 찾는다', () => {
    expect(ids(filterPapers(papers, { ...emptyFilter(), text: '  GRAPH networks ' }))).toEqual([1])
    expect(ids(filterPapers(papers, { ...emptyFilter(), text: 'vaswani' }))).toEqual([2])
    expect(ids(filterPapers(papers, { ...emptyFilter(), text: 'arxiv' }))).toEqual([2])
    expect(ids(filterPapers(papers, { ...emptyFilter(), text: '10.1145' }))).toEqual([3])
    expect(ids(filterPapers(papers, { ...emptyFilter(), text: 'gnn' }))).toEqual([1, 3])
    expect(ids(filterPapers(papers, { ...emptyFilter(), text: 'graph attention' }))).toEqual([])
  })

  it('태그는 고른 태그를 모두 가진 논문만 남긴다', () => {
    expect(ids(filterPapers(papers, { ...emptyFilter(), tags: ['gnn'] }))).toEqual([1, 3])
    expect(ids(filterPapers(papers, { ...emptyFilter(), tags: ['gnn', 'survey'] }))).toEqual([1])
  })

  it('항목 종류는 고른 것 가운데 하나면 남긴다', () => {
    expect(ids(filterPapers(papers, { ...emptyFilter(), itemTypes: ['preprint', 'report'] }))).toEqual([2, 4])
  })

  it('읽기 상태는 고른 것 가운데 하나면 남긴다', () => {
    expect(ids(filterPapers(papers, { ...emptyFilter(), readStatuses: ['read', 'reading'] }))).toEqual([2, 3])
    expect(ids(filterPapers(papers, { ...emptyFilter(), readStatuses: ['to-read'] }))).toEqual([1, 4])
    expect(isFilterActive({ ...emptyFilter(), readStatuses: ['read'] })).toBe(true)
  })

  it('연도는 양 끝을 포함하고, 연도 조건이 있으면 연도 없는 논문은 뺀다', () => {
    expect(ids(filterPapers(papers, { ...emptyFilter(), yearFrom: 2017, yearTo: 2019 }))).toEqual([1, 2])
    expect(ids(filterPapers(papers, { ...emptyFilter(), yearFrom: 2020 }))).toEqual([3])
    expect(ids(filterPapers(papers, { ...emptyFilter(), yearTo: 2017 }))).toEqual([2])
  })

  it('조건을 모두 함께 적용한다', () => {
    const filter = { ...emptyFilter(), tags: ['gnn'], yearFrom: 2020, itemTypes: ['conference-paper'] }
    expect(ids(filterPapers(papers, filter))).toEqual([3])
  })
})

describe('isFilterActive', () => {
  it('조건이 하나라도 있으면 참이다', () => {
    expect(isFilterActive(emptyFilter())).toBe(false)
    expect(isFilterActive({ ...emptyFilter(), text: '   ' })).toBe(false)
    expect(isFilterActive({ ...emptyFilter(), text: 'x' })).toBe(true)
    expect(isFilterActive({ ...emptyFilter(), tags: ['a'] })).toBe(true)
    expect(isFilterActive({ ...emptyFilter(), itemTypes: ['book'] })).toBe(true)
    expect(isFilterActive({ ...emptyFilter(), yearTo: 2000 })).toBe(true)
  })
})

describe('tagCounts', () => {
  it('태그마다 논문 수를 세어 이름순으로 돌려준다', () => {
    expect(tagCounts(papers)).toEqual([
      { name: 'gnn', count: 2 },
      { name: 'nlp', count: 1 },
      { name: 'survey', count: 1 },
    ])
    expect(tagCounts([])).toEqual([])
  })
})
