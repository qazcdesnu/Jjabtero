// @doc: docs/design/LibraryView.md#4-테스트
// @doc: docs/design/LibraryFilter.md#5-테스트
// @doc: docs/design/ReadingStatus.md#4-테스트

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
    read_status: 'to-read',
    note: null,
    created_at: '2026-11-01T00:00:00',
    updated_at: '2026-11-01T00:00:00',
  }
}

function setup(overrides: Partial<Parameters<typeof createLibraryState>[0]> = {}) {
  const deps = {
    listPapers: vi.fn().mockResolvedValue([paper(2), paper(1)]),
    deletePaper: vi.fn().mockResolvedValue(undefined),
    updateReading: vi.fn(async (id: number, update: object) => ({ ...paper(id), ...update })),
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

describe('필터', () => {
  const tagged = (id: number, tags: string[]) => ({ ...paper(id), tags })

  it('visible은 필터를 적용하고 tags는 서재 전체를 센다', async () => {
    const { library } = setup({
      listPapers: vi.fn().mockResolvedValue([tagged(1, ['gnn']), tagged(2, ['nlp']), tagged(3, ['gnn'])]),
    })
    await library.load()
    library.toggleTag('gnn')
    expect(library.visible.value.map((p) => p.id)).toEqual([1, 3])
    expect(library.tags.value).toEqual([
      { name: 'gnn', count: 2 },
      { name: 'nlp', count: 1 },
    ])
  })

  it('toggleTag는 넣고 빼며, clearFilter는 처음으로 돌린다', async () => {
    const { library } = setup()
    library.toggleTag('a')
    library.toggleTag('b')
    library.toggleTag('a')
    expect(library.state.filter.tags).toEqual(['b'])
    library.state.filter.text = 'x'
    library.clearFilter()
    expect(library.state.filter).toEqual({ text: '', tags: [], itemTypes: [], readStatuses: [], yearFrom: null, yearTo: null })
  })

  it('고른 논문이 거르기로 사라지면 상세도 빈다', async () => {
    const { library } = setup({ listPapers: vi.fn().mockResolvedValue([tagged(1, ['gnn']), tagged(2, [])]) })
    await library.load()
    library.select(paper(2))
    expect(library.selected.value?.id).toBe(2)
    library.toggleTag('gnn')
    expect(library.selected.value).toBeNull()
    library.clearFilter()
    expect(library.selected.value?.id).toBe(2)
  })
})

describe('changeReading', () => {
  it('성공하면 목록의 논문을 응답으로 바꾼다', async () => {
    const { library, deps } = setup()
    await library.load()
    await expect(library.changeReading(paper(2), { read_status: 'read', note: '메모' })).resolves.toBe(true)
    expect(deps.updateReading).toHaveBeenCalledWith(2, { read_status: 'read', note: '메모' })
    expect(library.state.papers.find((p) => p.id === 2)).toMatchObject({ read_status: 'read', note: '메모' })
  })

  it('404면 목록에서 빼고, 그 밖의 실패는 오류로 둔다', async () => {
    const missing = setup({ updateReading: vi.fn().mockRejectedValue(new PaperNotFoundError(2)) })
    await missing.library.load()
    await expect(missing.library.changeReading(paper(2), { read_status: 'read' })).resolves.toBe(false)
    expect(missing.library.state.papers.map((p) => p.id)).toEqual([1])

    const failing = setup({ updateReading: vi.fn().mockRejectedValue(new Error('저장 실패: 500')) })
    await failing.library.load()
    await failing.library.changeReading(paper(2), { note: 'x' })
    expect(failing.library.state.readingError).toBe('저장 실패: 500')
    expect(failing.library.state.papers.map((p) => p.id)).toEqual([2, 1])
  })
})

