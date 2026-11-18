// @doc: docs/design/LibraryView.md#2-화면-상태
// @doc: docs/design/LibraryFilter.md#3-화면-상태
// @doc: docs/design/ReadingStatus.md#3-화면
// @doc: docs/design/Tags.md#4-화면

import { computed, reactive } from 'vue'
import {
  PaperNotFoundError,
  applyTags,
  deletePaper,
  deleteTag,
  listPapers,
  renameTag,
  setPaperTags,
  updateReading,
  type Paper,
} from './api'
import { timeKey } from './labels'
import { emptyFilter, filterPapers, tagCounts } from './libraryFilter'

// 서재 표의 시각 열 정렬 키. 표가 다시 만들어져도 같은 함수여야 고른 정렬 열이 표시되므로 모듈에 둔다.
// @doc: docs/design/LibraryView.md#2-화면-상태
export const SORT_BY_ADDED = (paper: Paper): string => timeKey(paper.created_at)
// @doc: docs/design/LibraryView.md#2-화면-상태
export const SORT_BY_READ = (paper: Paper): string => timeKey(paper.last_read_at)

// @doc: docs/design/LibraryView.md#2-화면-상태
export type SortField = string | ((paper: Paper) => string) | undefined

// @doc: docs/design/LibraryView.md#2-화면-상태
// @doc: docs/design/LibraryFilter.md#3-화면-상태
// @doc: docs/design/ReadingStatus.md#3-화면
// @doc: docs/design/Tags.md#4-화면
export function createLibraryState(
  deps = { listPapers, deletePaper, updateReading, setPaperTags, applyTags, renameTag, deleteTag },
) {
  const state = reactive({
    papers: [] as Paper[],
    loading: false,
    error: '',
    selectedId: null as number | null,
    removeError: '',
    readingError: '',
    filter: emptyFilter(),
    // 여러 편에 태그를 붙이려고 고른 논문 ID
    checked: [] as number[],
    tagError: '',
    // 표의 정렬. 리더를 열고 닫으면 표가 다시 만들어지므로 여기에 두어 지킨다. 순서 1은 오름차순, -1은 내림차순이다
    sortField: undefined as SortField,
    sortOrder: undefined as number | undefined,
  })

  const visible = computed(() => filterPapers(state.papers, state.filter))
  const tags = computed(() => tagCounts(state.papers))
  const selected = computed(
    () => visible.value.find((paper) => paper.id === state.selectedId) ?? null,
  )

  async function load(): Promise<void> {
    state.loading = true
    state.error = ''
    try {
      state.papers = await deps.listPapers()
      if (!state.papers.some((paper) => paper.id === state.selectedId)) {
        state.selectedId = null
      }
      state.checked = state.checked.filter((id) => state.papers.some((paper) => paper.id === id))
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
    } finally {
      state.loading = false
    }
  }

  function select(paper: Paper | null): void {
    state.selectedId = paper ? paper.id : null
    state.removeError = ''
    state.readingError = ''
  }

  function forget(paperId: number): void {
    state.papers = state.papers.filter((paper) => paper.id !== paperId)
    if (state.selectedId === paperId) {
      state.selectedId = null
    }
  }

  async function remove(paper: Paper): Promise<void> {
    state.removeError = ''
    try {
      await deps.deletePaper(paper.id)
      forget(paper.id)
    } catch (error) {
      if (error instanceof PaperNotFoundError) {
        forget(paper.id)
      } else {
        state.removeError = error instanceof Error ? error.message : String(error)
      }
    }
  }

  async function changeReading(
    paper: Paper,
    update: { read_status?: string; note?: string | null },
  ): Promise<boolean> {
    state.readingError = ''
    try {
      const changed = await deps.updateReading(paper.id, update)
      state.papers = state.papers.map((item) => (item.id === changed.id ? changed : item))
      return true
    } catch (error) {
      if (error instanceof PaperNotFoundError) {
        forget(paper.id)
      } else {
        state.readingError = error instanceof Error ? error.message : String(error)
      }
      return false
    }
  }

  function toggleTag(name: string): void {
    const tags = state.filter.tags
    state.filter.tags = tags.includes(name) ? tags.filter((tag) => tag !== name) : [...tags, name]
  }

  function clearFilter(): void {
    state.filter = emptyFilter()
  }

  async function tagAction(action: () => Promise<unknown>): Promise<boolean> {
    state.tagError = ''
    try {
      await action()
      return true
    } catch (error) {
      state.tagError = error instanceof Error ? error.message : String(error)
      return false
    }
  }

  // 논문 한 편의 태그를 바꾼다.
  function setTags(paper: Paper, names: string[]): Promise<boolean> {
    return tagAction(async () => {
      const changed = await deps.setPaperTags(paper.id, names)
      state.papers = state.papers.map((item) => (item.id === changed.id ? changed : item))
    })
  }

  function toggleChecked(paperId: number): void {
    state.checked = state.checked.includes(paperId)
      ? state.checked.filter((id) => id !== paperId)
      : [...state.checked, paperId]
  }

  // 보이는 논문을 모두 고르거나, 이미 모두 골랐으면 고르기를 푼다.
  function toggleAllVisible(): void {
    const ids = visible.value.map((paper) => paper.id)
    const all = ids.length > 0 && ids.every((id) => state.checked.includes(id))
    state.checked = all ? state.checked.filter((id) => !ids.includes(id)) : [...new Set([...state.checked, ...ids])]
  }

  // 고른 논문들에 태그를 붙이거나 뗀다.
  function tagChecked(names: string[], mode: 'add' | 'remove'): Promise<boolean> {
    return tagAction(async () => {
      await deps.applyTags(state.checked, mode === 'add' ? names : [], mode === 'remove' ? names : [])
      await load()
    })
  }

  // 태그 이름을 바꾼다. 필터에 있던 태그는 새 이름으로 바꾼다.
  function renameTagEverywhere(name: string, newName: string): Promise<boolean> {
    return tagAction(async () => {
      await deps.renameTag(name, newName)
      const renamed = newName.replace(/\s+/g, ' ').trim()
      state.filter.tags = [...new Set(state.filter.tags.map((tag) => (tag === name ? renamed : tag)))]
      await load()
    })
  }

  // 태그를 지운다. 필터에서도 뺀다.
  function deleteTagEverywhere(name: string): Promise<boolean> {
    return tagAction(async () => {
      await deps.deleteTag(name)
      state.filter.tags = state.filter.tags.filter((tag) => tag !== name)
      await load()
    })
  }

  return {
    state,
    visible,
    tags,
    selected,
    load,
    select,
    remove,
    changeReading,
    toggleTag,
    clearFilter,
    setTags,
    toggleChecked,
    toggleAllVisible,
    tagChecked,
    renameTagEverywhere,
    deleteTagEverywhere,
  }
}
