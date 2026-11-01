// @doc: docs/design/PaperSearch.md#4-화면

import { computed, reactive } from 'vue'
import {
  DuplicatePaperError,
  addPaper,
  searchPapers,
  toPaperInput,
  type SearchResult,
} from './api'

// @doc: docs/design/PaperSearch.md#4-화면
export const SEARCH_SOURCES = [
  { name: 'openalex', label: 'OpenAlex' },
  { name: 'arxiv', label: 'arXiv' },
] as const

// @doc: docs/design/PaperSearch.md#4-화면
export const ITEM_TYPE_LABELS: Record<string, string> = {
  'journal-article': '저널 논문',
  'conference-paper': '학회 논문',
  preprint: '프리프린트',
  book: '책',
  'book-chapter': '책의 장',
  thesis: '학위논문',
  report: '보고서',
  other: '그 밖',
}

// @doc: docs/design/PaperSearch.md#4-화면
export function sourceLabel(name: string): string {
  return SEARCH_SOURCES.find((source) => source.name === name)?.label ?? name
}

// @doc: docs/design/PaperSearch.md#4-화면
export function resultKey(result: SearchResult): string {
  return `${result.source}:${result.source_id}`
}

// @doc: docs/design/PaperSearch.md#4-화면
export function createSearchState(deps = { searchPapers, addPaper }) {
  const state = reactive({
    query: '',
    sources: SEARCH_SOURCES.map((source) => source.name as string),
    searching: false,
    error: '',
    results: [] as SearchResult[],
    failures: [] as { source: string; message: string }[],
    selectedKey: null as string | null,
    addedKeys: [] as string[],
    addErrors: {} as Record<string, string>,
  })

  const rows = computed(() => state.results.map((result) => ({ ...result, key: resultKey(result) })))
  const selected = computed(
    () => state.results.find((result) => resultKey(result) === state.selectedKey) ?? null,
  )
  const canRun = computed(() => state.query.trim() !== '' && state.sources.length > 0)

  async function run(): Promise<void> {
    if (!canRun.value) return
    state.searching = true
    state.error = ''
    try {
      const response = await deps.searchPapers(state.query.trim(), state.sources)
      state.results = response.results
      state.failures = response.errors
      state.selectedKey = null
      state.addedKeys = []
      state.addErrors = {}
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
    } finally {
      state.searching = false
    }
  }

  function select(result: SearchResult | null): void {
    state.selectedKey = result ? resultKey(result) : null
  }

  function isInLibrary(result: SearchResult): boolean {
    return result.library_paper_id !== null || state.addedKeys.includes(resultKey(result))
  }

  async function add(result: SearchResult, tags: string[]): Promise<void> {
    const key = resultKey(result)
    delete state.addErrors[key]
    try {
      await deps.addPaper(toPaperInput(result, tags))
      state.addedKeys.push(key)
    } catch (error) {
      if (error instanceof DuplicatePaperError) {
        state.addedKeys.push(key)
      } else {
        state.addErrors[key] = error instanceof Error ? error.message : String(error)
      }
    }
  }

  return { state, rows, selected, canRun, run, select, isInLibrary, add }
}
