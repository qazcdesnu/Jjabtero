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
    // 태그를 고른 채 담을 때 확인 창에 띄운 논문과, 붙이려고 체크한 태그
    confirming: null as GraphNode | null,
    chosenTags: [] as string[],
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

  // 서재 밖 논문을 담고(붙일 태그와 함께) 그래프를 다시 읽어, 같은 논문의 서재 점을 고른다.
  async function add(node: GraphNode, tagNames: string[] = []): Promise<void> {
    if (!node.openalex_id) return
    state.adding = true
    state.addError = ''
    try {
      await deps.addPaper({
        ...citedWorkInput({ ...node, openalex_id: node.openalex_id, shared_refs: null, library_paper_id: null }),
        tags: [...tagNames],
      })
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

  // 태그를 골라 두었으면 그 태그를 붙일지 확인 창으로 묻고(처음에는 모두 체크), 아니면 바로 담는다.
  function requestAdd(node: GraphNode): Promise<void> {
    if (tags().length === 0) return add(node)
    state.confirming = node
    state.chosenTags = [...tags()]
    return Promise.resolve()
  }

  function confirmAdd(): Promise<void> {
    const node = state.confirming
    state.confirming = null
    return node ? add(node, state.chosenTags) : Promise.resolve()
  }

  function cancelAdd(): void {
    state.confirming = null
  }

  return { state, selected, load, select, add, requestAdd, confirmAdd, cancelAdd }
}
