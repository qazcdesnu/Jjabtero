// @doc: docs/design/AppSkeleton.md#3-프론트엔드-앱
// @doc: docs/design/PaperSearch.md#4-화면

// @doc: docs/design/AppSkeleton.md#3-프론트엔드-앱
export interface Health {
  status: string
  version: string
}

// @doc: docs/design/AppSkeleton.md#3-프론트엔드-앱
export async function fetchHealth(): Promise<Health> {
  const response = await fetch('/api/health')
  if (!response.ok) {
    throw new Error(`서버 상태 확인 실패: ${response.status}`)
  }
  return (await response.json()) as Health
}

// @doc: docs/design/PaperSearch.md#4-화면
export interface SearchResult {
  source: string
  source_id: string
  title: string
  authors: string[]
  item_type: string
  year: number | null
  venue: string | null
  doi: string | null
  url: string | null
  library_paper_id: number | null
}

// @doc: docs/design/PaperSearch.md#4-화면
export interface SearchResponse {
  results: SearchResult[]
  errors: { source: string; message: string }[]
}

// @doc: docs/design/PaperSearch.md#4-화면
export interface PaperInput {
  title: string
  authors: string[]
  item_type: string
  year: number | null
  venue: string | null
  doi: string | null
  url: string | null
  tags: string[]
}

// @doc: docs/design/PaperSearch.md#4-화면
export interface Paper extends PaperInput {
  id: number
  created_at: string
  updated_at: string
}

// @doc: docs/design/PaperSearch.md#4-화면
export class DuplicatePaperError extends Error {
  readonly paperId: number

  constructor(paperId: number) {
    super(`이미 서재에 있는 논문입니다: ${paperId}`)
    this.paperId = paperId
  }
}

// @doc: docs/design/PaperSearch.md#4-화면
export async function searchPapers(query: string, sources: string[]): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query })
  for (const source of sources) {
    params.append('sources', source)
  }
  const response = await fetch(`/api/search?${params}`)
  if (!response.ok) {
    throw new Error(`검색 실패: ${response.status}`)
  }
  return (await response.json()) as SearchResponse
}

// @doc: docs/design/PaperSearch.md#4-화면
export async function addPaper(input: PaperInput): Promise<Paper> {
  const response = await fetch('/api/papers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (response.status === 409) {
    const body = (await response.json()) as { detail: { paper_id: number } }
    throw new DuplicatePaperError(body.detail.paper_id)
  }
  if (!response.ok) {
    throw new Error(`논문 추가 실패: ${response.status}`)
  }
  return (await response.json()) as Paper
}

// @doc: docs/design/PaperSearch.md#4-화면
export function toPaperInput(result: SearchResult, tags: string): PaperInput {
  return {
    title: result.title,
    authors: result.authors,
    item_type: result.item_type,
    year: result.year,
    venue: result.venue,
    doi: result.doi,
    url: result.url,
    tags: tags
      .split(',')
      .map((tag) => tag.trim())
      .filter((tag) => tag !== ''),
  }
}
