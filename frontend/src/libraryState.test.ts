// @doc: docs/design/LibraryView.md#4-테스트

import { describe, expect, it, vi } from 'vitest'
import { PaperNotFoundError, type Paper } from './api'
import { createLibraryState } from './libraryState'

function paper(id: number): Paper {
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
    created_at: '2026-11-01T00:00:00',
    updated_at: '2026-11-01T00:00:00',
  }
}

function setup(overrides: Partial<Parameters<typeof createLibraryState>[0]> = {}) {
  const deps = {
    listPapers: vi.fn().mockResolvedValue([paper(2), paper(1)]),
    deletePaper: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
  return { library: createLibraryState(deps), deps }
}

describe('createLibraryState', () => {
  it('목록을 불러온다', async () => {
    const { library } = setup()
    await library.load()
    expect(library.state.papers.map((p) => p.id)).toEqual([2, 1])
    expect(library.state.loading).toBe(false)
    expect(library.state.error).toBe('')
  })

  it('불러오기가 실패하면 오류를 담는다', async () => {
    const { library } = setup({ listPapers: vi.fn().mockRejectedValue(new Error('서재 불러오기 실패: 500')) })
    await library.load()
    expect(library.state.error).toBe('서재 불러오기 실패: 500')
    expect(library.state.loading).toBe(false)
  })

  it('고른 논문이 새 목록에 있으면 유지하고 없으면 비운다', async () => {
    const listPapers = vi
      .fn()
      .mockResolvedValueOnce([paper(1), paper(2)])
      .mockResolvedValueOnce([paper(1)])
      .mockResolvedValueOnce([paper(1)])
    const { library } = setup({ listPapers })
    await library.load()
    library.select(paper(2))
    expect(library.selected.value?.id).toBe(2)
    await library.load()
    expect(library.selected.value).toBeNull()
    library.select(paper(1))
    await library.load()
    expect(library.selected.value?.id).toBe(1)
  })

  it('지우면 목록에서 빼고 고른 것을 비운다', async () => {
    const { library, deps } = setup()
    await library.load()
    library.select(paper(2))
    await library.remove(paper(2))
    expect(deps.deletePaper).toHaveBeenCalledWith(2)
    expect(library.state.papers.map((p) => p.id)).toEqual([1])
    expect(library.selected.value).toBeNull()
  })

  it('404면 이미 없는 것이므로 목록에서 뺀다', async () => {
    const { library } = setup({ deletePaper: vi.fn().mockRejectedValue(new PaperNotFoundError(2)) })
    await library.load()
    await library.remove(paper(2))
    expect(library.state.papers.map((p) => p.id)).toEqual([1])
    expect(library.state.removeError).toBe('')
  })

  it('그 밖의 삭제 실패는 오류로 두고 목록은 그대로다', async () => {
    const { library } = setup({ deletePaper: vi.fn().mockRejectedValue(new Error('논문 삭제 실패: 500')) })
    await library.load()
    await library.remove(paper(2))
    expect(library.state.papers.map((p) => p.id)).toEqual([2, 1])
    expect(library.state.removeError).toBe('논문 삭제 실패: 500')
  })
})
