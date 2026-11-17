// @doc: docs/design/CitationGraph.md#4-화면

import { computed, reactive } from 'vue'
import { DuplicatePaperError, addPaper, fetchCitationGraph, type CitationGraph, type GraphNode } from './api'
import { citedWorkInput } from './citationListState'

// @doc: docs/design/CitationGraph.md#4-화면
export const OUTSIDE_COUNT = 15

// @doc: docs/design/CitationGraph.md#4-화면
// @doc: docs/design/Tags.md#5-태그별-그래프
export function createGraphState(
  onAdded: () => Promise<void> | void,
  deps = { fetchCitationGraph, addPaper },
  // 왼쪽에서 고른 태그. 그 태그를 모두 가진 서재 논문만으로 그린다.
  tags: () => string[] = () => [],
) {
  const state = reactive({
    data: null as CitationGraph | null,
    loading: false,
    error: '',
    outside: false,
    selectedId: null as string | null,
    adding: false,
    addError: '',
  })
  const selected = computed<GraphNode | null>(
    () => state.data?.nodes.find((node) => node.id === state.selectedId) ?? null,
  )

  async function load(): Promise<void> {
    state.loading = true
    state.error = ''
    try {
      state.data = await deps.fetchCitationGraph(state.outside ? OUTSIDE_COUNT : 0, [...tags()])
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
    } finally {
      state.loading = false
    }
  }

  function select(id: string | null): void {
    state.selectedId = id
    state.addError = ''
  }

  // 서재 밖 논문을 담고 그래프를 다시 읽어, 같은 논문의 서재 점을 고른다.
  async function add(node: GraphNode): Promise<void> {
    if (!node.openalex_id) return
    state.adding = true
    state.addError = ''
    try {
      await deps.addPaper(
        citedWorkInput({ ...node, openalex_id: node.openalex_id, shared_refs: null, library_paper_id: null }),
      )
      await onAdded()
    } catch (error) {
      if (!(error instanceof DuplicatePaperError)) {
        state.addError = error instanceof Error ? error.message : String(error)
        return
      }
    } finally {
      state.adding = false
    }
    await load()
    const added = state.data?.nodes.find((item) => item.paper_id !== null && item.openalex_id === node.openalex_id)
    state.selectedId = added ? added.id : null
  }

  return { state, selected, load, select, add }
}
