// @doc: docs/design/LibraryView.md#4-테스트
// @doc: docs/design/LibraryFilter.md#5-테스트
// @doc: docs/design/ReadingStatus.md#4-테스트
// @doc: docs/design/Tags.md#6-테스트

import { describe, expect, it, vi } from 'vitest'
import { PaperNotFoundError, type Paper } from './api'
import { SORT_BY_ADDED, SORT_BY_READ, createLibraryState } from './libraryState'

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
    last_read_at: '2026-11-01T00:00:00',
    updated_at: '2026-11-01T00:00:00',
  }
}

function setup(overrides: Partial<Parameters<typeof createLibraryState>[0]> = {}) {
  const deps = {
    listPapers: vi.fn().mockResolvedValue([paper(2), paper(1)]),
    deletePaper: vi.fn().mockResolvedValue(undefined),
    updateReading: vi.fn(async (id: number, update: object) => ({ ...paper(id), ...update })),
    setPaperTags: vi.fn(async (id: number, tags: string[]) => ({ ...paper(id), tags: [...tags].sort() })),
    applyTags: vi.fn().mockResolvedValue(1),
    renameTag: vi.fn().mockResolvedValue(1),
    deleteTag: vi.fn().mockResolvedValue(1),
    ...overrides,
  }
  return { library: createLibraryState(deps), deps }
}

describe('createLibraryState', () => {
  it('시각 열은 시각 순서로 정렬하고, 다시 불러와도 고른 정렬을 지킨다', async () => {
    const read = { ...paper(1), created_at: '2026-11-17T19:48:12.5', last_read_at: '2026-11-18T01:58:17+00:00' }
    expect(SORT_BY_ADDED(read)).toBe('2026-11-17T19:48:12.500Z')
    expect(SORT_BY_READ(read)).toBe('2026-11-18T01:58:17.000Z')
    const { library } = setup()
    library.state.sortField = SORT_BY_READ
    library.state.sortOrder = -1
    await library.load()
    expect([library.state.sortField, library.state.sortOrder]).toEqual([SORT_BY_READ, -1])
  })

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

  it('논문 한 편의 태그를 바꾸면 목록의 그 논문을 바꾸고, 실패하면 까닭을 둔다', async () => {
    const { library, deps } = setup()
    await library.load()
    expect(await library.setTags(paper(1), ['b', 'a'])).toBe(true)
    expect(deps.setPaperTags).toHaveBeenCalledWith(1, ['b', 'a'])
    expect(library.state.papers.find((item) => item.id === 1)?.tags).toEqual(['a', 'b'])
    vi.mocked(deps.setPaperTags).mockRejectedValueOnce(new Error('태그 이름은 50자까지입니다'))
    expect(await library.setTags(paper(1), ['x'])).toBe(false)
    expect(library.state.tagError).toContain('50자')
  })

  it('여러 편을 고르고 태그를 붙이거나 떼며, 보이는 논문 모두 고르기를 켜고 끈다', async () => {
    const { library, deps } = setup()
    await library.load()
    library.toggleChecked(2)
    expect(library.state.checked).toEqual([2])
    library.toggleAllVisible()
    expect([...library.state.checked].sort()).toEqual([1, 2])
    await library.tagChecked(['survey'], 'add')
    expect(deps.applyTags).toHaveBeenCalledWith([2, 1], ['survey'], [])
    await library.tagChecked(['survey'], 'remove')
    expect(deps.applyTags).toHaveBeenLastCalledWith([2, 1], [], ['survey'])
    library.toggleAllVisible()
    expect(library.state.checked).toEqual([])
  })

  it('태그 이름을 바꾸거나 지우면 필터의 그 태그도 바꾸거나 뺀다', async () => {
    const { library, deps } = setup()
    await library.load()
    library.toggleTag('nlp')
    library.toggleTag('cv')
    await library.renameTagEverywhere('nlp', '  language ')
    expect(deps.renameTag).toHaveBeenCalledWith('nlp', '  language ')
    expect(library.state.filter.tags).toEqual(['language', 'cv'])
    await library.deleteTagEverywhere('cv')
    expect(library.state.filter.tags).toEqual(['language'])
  })

  it('다시 불러오면 서재에 없는 논문은 고르기에서 뺀다', async () => {
    const { library, deps } = setup()
    await library.load()
    library.toggleChecked(1)
    library.toggleChecked(2)
    vi.mocked(deps.listPapers).mockResolvedValue([paper(2)])
    await library.load()
    expect(library.state.checked).toEqual([2])
  })
})
