// @doc: docs/design/Citations.md#6-api와-화면

import { reactive } from 'vue'
import {
  DuplicatePaperError,
  addPaper,
  fetchPaperCitations,
  type CitedWork,
  type PaperCitations,
  type PaperInput,
} from './api'

// @doc: docs/design/Citations.md#6-api와-화면
export function citedWorkInput(work: CitedWork): PaperInput {
  return {
    title: work.title ?? work.openalex_id,
    authors: work.authors,
    item_type: work.item_type,
    year: work.year,
    venue: work.venue,
    doi: work.doi,
    url: work.doi ? `https://doi.org/${work.doi}` : `https://openalex.org/${work.openalex_id}`,
    tags: [],
    openalex_id: work.openalex_id,
  }
}

// @doc: docs/design/Citations.md#6-api와-화면
export function createCitationListState(
  onAdded: () => Promise<void> | void,
  deps = { fetchPaperCitations, addPaper },
) {
  const state = reactive({
    data: null as PaperCitations | null,
    loading: false,
    error: '',
    adding: [] as string[],
    addErrors: {} as Record<string, string>,
  })
  let currentPaper: number | null = null

  async function load(paperId: number): Promise<void> {
    currentPaper = paperId
    state.loading = true
    state.error = ''
    try {
      const data = await deps.fetchPaperCitations(paperId)
      if (currentPaper === paperId) state.data = data
    } catch (error) {
      if (currentPaper === paperId) state.error = error instanceof Error ? error.message : String(error)
    } finally {
      if (currentPaper === paperId) state.loading = false
    }
  }

  function mark(workId: string, paperId: number): void {
    if (!state.data) return
    for (const list of [state.data.references, state.data.citations]) {
      for (const item of list) if (item.openalex_id === workId) item.library_paper_id = paperId
    }
  }

  async function add(work: CitedWork): Promise<void> {
    state.adding = [...state.adding, work.openalex_id]
    delete state.addErrors[work.openalex_id]
    try {
      const paper = await deps.addPaper(citedWorkInput(work))
      mark(work.openalex_id, paper.id)
      await onAdded()
    } catch (error) {
      if (error instanceof DuplicatePaperError) mark(work.openalex_id, error.paperId)
      else state.addErrors[work.openalex_id] = error instanceof Error ? error.message : String(error)
    } finally {
      state.adding = state.adding.filter((id) => id !== work.openalex_id)
    }
  }

  return { state, load, add }
}
