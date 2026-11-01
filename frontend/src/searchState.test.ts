// @doc: docs/design/PaperSearch.md#5-테스트

import { describe, expect, it, vi } from 'vitest'
import { DuplicatePaperError, type SearchResult } from './api'
import { createSearchState, resultKey, sourceLabel } from './searchState'

const result: SearchResult = {
  source: 'openalex',
  source_id: 'W1',
  title: 'Attention Is All You Need',
  authors: ['Ashish Vaswani'],
  item_type: 'preprint',
  year: 2017,
  venue: 'arXiv',
  doi: '10.48550/arxiv.1706.03762',
  url: null,
  library_paper_id: null,
}

function setup(overrides: Partial<Parameters<typeof createSearchState>[0]> = {}) {
  const deps = {
    searchPapers: vi.fn().mockResolvedValue({ results: [result], errors: [] }),
    addPaper: vi.fn().mockResolvedValue({}),
    ...overrides,
  }
  return { search: createSearchState(deps), deps }
}

describe('createSearchState', () => {
  it('검색하면 결과와 실패를 담고 고른 결과를 비운다', async () => {
    const failures = [{ source: 'arxiv', message: 'down' }]
    const { search, deps } = setup({
      searchPapers: vi.fn().mockResolvedValue({ results: [result], errors: failures }),
    })
    search.state.query = '  attention  '
    search.state.selectedKey = 'old'

    await search.run()

    expect(deps.searchPapers).toHaveBeenCalledWith('attention', ['openalex', 'arxiv'])
    expect(search.state.results).toEqual([result])
    expect(search.state.failures).toEqual(failures)
    expect(search.state.selectedKey).toBeNull()
    expect(search.rows.value[0]?.key).toBe('openalex:W1')
    expect(search.state.searching).toBe(false)
  })

  it('검색어가 비거나 검색원이 없으면 검색하지 않는다', async () => {
    const { search, deps } = setup()
    search.state.query = '   '
    await search.run()
    search.state.query = 'x'
    search.state.sources = []
    await search.run()
    expect(deps.searchPapers).not.toHaveBeenCalled()
    expect(search.canRun.value).toBe(false)
  })

  it('검색이 실패하면 오류를 담는다', async () => {
    const { search } = setup({ searchPapers: vi.fn().mockRejectedValue(new Error('검색 실패: 500')) })
    search.state.query = 'x'
    await search.run()
    expect(search.state.error).toBe('검색 실패: 500')
    expect(search.state.searching).toBe(false)
  })

  it('고른 결과를 열쇠로 찾는다', async () => {
    const { search } = setup()
    search.state.query = 'x'
    await search.run()
    search.select(result)
    expect(search.state.selectedKey).toBe(resultKey(result))
    expect(search.selected.value).toEqual(result)
    search.select(null)
    expect(search.selected.value).toBeNull()
  })

  it('추가에 성공하면 태그와 함께 보내고 서재에 있는 것으로 표시한다', async () => {
    const { search, deps } = setup()
    expect(search.isInLibrary(result)).toBe(false)
    await search.add(result, ['nlp'])
    expect(deps.addPaper).toHaveBeenCalledWith(expect.objectContaining({ tags: ['nlp'] }))
    expect(search.isInLibrary(result)).toBe(true)
  })

  it('409면 서재에 있는 것으로 표시하고, 그 밖의 실패는 오류로 둔다', async () => {
    const duplicate = setup({ addPaper: vi.fn().mockRejectedValue(new DuplicatePaperError(3)) })
    await duplicate.search.add(result, [])
    expect(duplicate.search.isInLibrary(result)).toBe(true)

    const failing = setup({ addPaper: vi.fn().mockRejectedValue(new Error('논문 추가 실패: 500')) })
    await failing.search.add(result, [])
    expect(failing.search.isInLibrary(result)).toBe(false)
    expect(failing.search.state.addErrors[resultKey(result)]).toBe('논문 추가 실패: 500')
  })

  it('library_paper_id가 있으면 처음부터 서재에 있다', () => {
    const { search } = setup()
    expect(search.isInLibrary({ ...result, library_paper_id: 1 })).toBe(true)
  })
})

describe('표시 이름', () => {
  it('검색원 이름을 표시 이름으로 바꾸고, 모르는 이름은 그대로 둔다', () => {
    expect(sourceLabel('openalex')).toBe('OpenAlex')
    expect(sourceLabel('arxiv')).toBe('arXiv')
    expect(sourceLabel('unknown')).toBe('unknown')
  })
})
