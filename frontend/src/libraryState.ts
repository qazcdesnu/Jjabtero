// @doc: docs/design/LibraryView.md#2-화면-상태
// @doc: docs/design/LibraryFilter.md#3-화면-상태

import { computed, reactive } from 'vue'
import { PaperNotFoundError, deletePaper, listPapers, type Paper } from './api'
import { emptyFilter, filterPapers, tagCounts } from './libraryFilter'

// @doc: docs/design/LibraryView.md#2-화면-상태
// @doc: docs/design/LibraryFilter.md#3-화면-상태
export function createLibraryState(deps = { listPapers, deletePaper }) {
  const state = reactive({
    papers: [] as Paper[],
    loading: false,
    error: '',
    selectedId: null as number | null,
    removeError: '',
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

  function toggleTag(name: string): void {
    const tags = state.filter.tags
    state.filter.tags = tags.includes(name) ? tags.filter((tag) => tag !== name) : [...tags, name]
  }

  function clearFilter(): void {
    state.filter = emptyFilter()
  }

  return { state, visible, tags, selected, load, select, remove, toggleTag, clearFilter }
}
