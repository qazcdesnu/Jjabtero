// @doc: docs/design/LibraryView.md#2-화면-상태
// @doc: docs/design/LibraryFilter.md#3-화면-상태
// @doc: docs/design/ReadingStatus.md#3-화면

import { computed, reactive } from 'vue'
import { PaperNotFoundError, deletePaper, listPapers, updateReading, type Paper } from './api'
import { emptyFilter, filterPapers, tagCounts } from './libraryFilter'

// @doc: docs/design/LibraryView.md#2-화면-상태
// @doc: docs/design/LibraryFilter.md#3-화면-상태
// @doc: docs/design/ReadingStatus.md#3-화면
export function createLibraryState(deps = { listPapers, deletePaper, updateReading }) {
  const state = reactive({
    papers: [] as Paper[],
    loading: false,
    error: '',
    selectedId: null as number | null,
    removeError: '',
    readingError: '',
    filter: emptyFilter(),
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

  return { state, visible, tags, selected, load, select, remove, changeReading, toggleTag, clearFilter }
}
