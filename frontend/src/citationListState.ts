// @doc: docs/design/Citations.md#6-api와-화면

import { reactive } from 'vue'
import {
  DuplicatePaperError,
  addPaper,
  fetchPaperCitations,
  fetchPaperRelated,
  type CitedWork,
  type Direction,
  type DirectionBasis,
  type PaperCitations,
  type PaperRelated,
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
export function relationReasons(work: {
  cites_paper: boolean
  cited_by_paper: boolean
  cocited: number
  shared_refs: number | null
}): string[] {
  const reasons: string[] = []
  if (work.cites_paper) reasons.push('이 논문을 인용')
  if (work.cited_by_paper) reasons.push('이 논문이 인용')
  if (work.cocited) reasons.push(`함께 인용 ${work.cocited}회`)
  if (work.shared_refs) reasons.push(`공유 참고문헌 ${work.shared_refs}`)
  return reasons
}

// @doc: docs/design/Citations.md#6-api와-화면
export function directionTag(
  direction: Direction | 'mixed' | null,
  basis: DirectionBasis | null = null,
): { label: string; hint: string; severity: 'info' | 'warn' | 'secondary' } | null {
  if (direction === 'mixed') return { label: '선행·후행', hint: '이어진 서재 논문에 따라 선행이기도 하고 후행이기도 합니다', severity: 'secondary' }
  if (direction === 'prior') {
    const hint = basis === 'citation' ? '기준 논문이 인용한 앞선 연구' : '기준 논문보다 먼저 공개된 논문'
    return { label: '선행', hint, severity: 'info' }
  }
  if (direction === 'later') {
    const hint = basis === 'citation' ? '기준 논문을 인용한 후속 연구' : '기준 논문보다 나중에 공개된 논문'
    return { label: '후행', hint, severity: 'warn' }
  }
  return null
}

// @doc: docs/design/Citations.md#6-api와-화면
export function createCitationListState(
  onAdded: () => Promise<void> | void,
  deps = { fetchPaperCitations, fetchPaperRelated, addPaper },
) {
  const state = reactive({
    data: null as PaperCitations | null,
    related: null as PaperRelated | null,
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
      const [data, related] = await Promise.all([deps.fetchPaperCitations(paperId), deps.fetchPaperRelated(paperId)])
      if (currentPaper === paperId) {
        state.data = data
        state.related = related
      }
    } catch (error) {
      if (currentPaper === paperId) state.error = error instanceof Error ? error.message : String(error)
    } finally {
      if (currentPaper === paperId) state.loading = false
    }
  }

  function mark(workId: string, paperId: number): void {
    const lists: CitedWork[][] = []
    if (state.data) lists.push(state.data.references, state.data.citations)
    if (state.related) lists.push(state.related.works)
    for (const list of lists) {
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
