// @doc: docs/design/Citations.md#6-api와-화면

import { reactive } from 'vue'
import { DuplicatePaperError, addPaper, fetchRecommendations, type Recommendations, type RecommendedWork } from './api'
import { citedWorkInput } from './citationListState'

// @doc: docs/design/Citations.md#6-api와-화면
export function createRecommendState(onAdded: () => Promise<void> | void, deps = { fetchRecommendations, addPaper }) {
  const state = reactive({
    data: null as Recommendations | null,
    loading: false,
    error: '',
    adding: [] as string[],
    added: [] as string[],
    addErrors: {} as Record<string, string>,
  })

  async function load(): Promise<void> {
    state.loading = true
    state.error = ''
    try {
      state.data = await deps.fetchRecommendations()
      state.added = []
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
    } finally {
      state.loading = false
    }
  }

  async function add(work: RecommendedWork): Promise<void> {
    state.adding = [...state.adding, work.openalex_id]
    delete state.addErrors[work.openalex_id]
    try {
      await deps.addPaper(citedWorkInput(work))
      state.added = [...state.added, work.openalex_id]
      await onAdded()
    } catch (error) {
      if (error instanceof DuplicatePaperError) state.added = [...state.added, work.openalex_id]
      else state.addErrors[work.openalex_id] = error instanceof Error ? error.message : String(error)
    } finally {
      state.adding = state.adding.filter((id) => id !== work.openalex_id)
    }
  }

  return { state, load, add }
}
