// @doc: docs/design/AppSkeleton.md#3-프론트엔드-앱
// @doc: docs/design/PaperSearch.md#4-화면
// @doc: docs/design/LibraryView.md#2-화면-상태
// @doc: docs/design/ReadingStatus.md#3-화면
// @doc: docs/design/DriveSync.md#7-화면

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
  // @doc: docs/design/Citations.md#2-서재-논문과-openalex-연결
  openalex_id?: string | null
}

// @doc: docs/design/PaperSearch.md#4-화면
export interface Paper extends PaperInput {
  // @doc: docs/design/Reader.md#5-api
  has_pdf?: boolean
  id: number
  read_status: string
  note: string | null
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
export function toPaperInput(result: SearchResult, tags: string[]): PaperInput {
  return {
    title: result.title,
    authors: result.authors,
    item_type: result.item_type,
    year: result.year,
    venue: result.venue,
    doi: result.doi,
    url: result.url,
    tags: [...new Set(tags.map((tag) => tag.trim()).filter((tag) => tag !== ''))],
    openalex_id: result.source === 'openalex' ? result.source_id : null,
  }
}

// @doc: docs/design/LibraryView.md#2-화면-상태
export class PaperNotFoundError extends Error {
  readonly paperId: number

  constructor(paperId: number) {
    super(`서재에 없는 논문입니다: ${paperId}`)
    this.paperId = paperId
  }
}

// @doc: docs/design/LibraryView.md#2-화면-상태
export async function listPapers(): Promise<Paper[]> {
  const response = await fetch('/api/papers')
  if (!response.ok) {
    throw new Error(`서재 불러오기 실패: ${response.status}`)
  }
  return (await response.json()) as Paper[]
}

// @doc: docs/design/LibraryView.md#2-화면-상태
export async function deletePaper(paperId: number): Promise<void> {
  const response = await fetch(`/api/papers/${paperId}`, { method: 'DELETE' })
  if (response.status === 404) {
    throw new PaperNotFoundError(paperId)
  }
  if (!response.ok) {
    throw new Error(`논문 삭제 실패: ${response.status}`)
  }
}

// @doc: docs/design/ReadingStatus.md#3-화면
export async function updateReading(
  paperId: number,
  update: { read_status?: string; note?: string | null },
): Promise<Paper> {
  const response = await fetch(`/api/papers/${paperId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  })
  if (response.status === 404) {
    throw new PaperNotFoundError(paperId)
  }
  if (!response.ok) {
    throw new Error(`저장 실패: ${response.status}`)
  }
  return (await response.json()) as Paper
}

// @doc: docs/design/DriveSync.md#7-화면
export interface DriveStatus {
  state: 'not_configured' | 'disconnected' | 'idle' | 'syncing' | 'conflict' | 'error'
  message: string
  last_synced_at: string | null
  pending: boolean
  data_version: number
}

async function driveRequest(path: string, init?: RequestInit): Promise<DriveStatus> {
  const response = await fetch(`/api/drive/${path}`, init)
  if (!response.ok) {
    throw new Error(`드라이브 요청 실패: ${response.status}`)
  }
  return (await response.json()) as DriveStatus
}

// @doc: docs/design/DriveSync.md#7-화면
export function fetchDriveStatus(): Promise<DriveStatus> {
  return driveRequest('status')
}

// @doc: docs/design/DriveSync.md#7-화면
export function syncDrive(): Promise<DriveStatus> {
  return driveRequest('sync', { method: 'POST' })
}

// @doc: docs/design/DriveSync.md#7-화면
export function resolveDrive(choice: 'remote' | 'local'): Promise<DriveStatus> {
  return driveRequest('resolve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ choice }),
  })
}

// @doc: docs/design/DriveSync.md#7-화면
export function disconnectDrive(): Promise<DriveStatus> {
  return driveRequest('disconnect', { method: 'POST' })
}

// @doc: docs/design/DriveSync.md#7-화면
export function driveConnectUrl(returnTo: string): string {
  return `/api/drive/connect?${new URLSearchParams({ return_to: returnTo })}`
}


// @doc: docs/design/Settings.md#3-api
export interface Setting {
  key: string
  label: string
  description: string
  value: number
  default: number
  minimum: number
  maximum: number
}

// @doc: docs/design/Settings.md#4-화면
export async function fetchSettings(): Promise<Setting[]> {
  const response = await fetch('/api/settings')
  if (!response.ok) {
    throw new Error(`설정 불러오기 실패: ${response.status}`)
  }
  return (await response.json()) as Setting[]
}

// @doc: docs/design/Settings.md#4-화면
export async function saveSettings(changes: Record<string, number>): Promise<Setting[]> {
  const response = await fetch('/api/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  })
  if (response.status === 422) {
    const body = await response.json()
    throw new Error(typeof body.detail === 'string' ? body.detail : '설정 값이 올바르지 않습니다.')
  }
  if (!response.ok) {
    throw new Error(`설정 저장 실패: ${response.status}`)
  }
  return (await response.json()) as Setting[]
}

// @doc: docs/design/Citations.md#6-api와-화면
export interface CitationStatus {
  papers: number
  linked: number
  not_found: number
  fetched: number
  running: boolean
  last_run: string | null
  error: string
}

async function citationRequest(path: string, init?: RequestInit): Promise<CitationStatus> {
  const response = await fetch(path, init)
  if (!response.ok) {
    throw new Error(`인용 데이터 요청 실패: ${response.status}`)
  }
  return (await response.json()) as CitationStatus
}

// @doc: docs/design/Citations.md#6-api와-화면
export function fetchCitationStatus(): Promise<CitationStatus> {
  return citationRequest('/api/citations/status')
}

// @doc: docs/design/Citations.md#6-api와-화면
export function refreshCitations(): Promise<CitationStatus> {
  return citationRequest('/api/citations/refresh', { method: 'POST' })
}

// @doc: docs/design/Reader.md#5-api
export interface PaperPdf {
  paper_id: number
  sha256: string
  size: number
  source: string
  source_url: string | null
  stored_in_drive: boolean
}

async function pdfResponse(response: Response): Promise<PaperPdf> {
  if (!response.ok) {
    let detail = ''
    try {
      const body = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : ''
    } catch {
      detail = ''
    }
    throw new Error(detail || `PDF 요청 실패: ${response.status}`)
  }
  return (await response.json()) as PaperPdf
}

// @doc: docs/design/Reader.md#5-api
export function pdfUrl(paperId: number): string {
  return `/api/papers/${paperId}/pdf`
}

// @doc: docs/design/Reader.md#5-api
export async function fetchOpenPdf(paperId: number): Promise<PaperPdf> {
  return pdfResponse(await fetch(`/api/papers/${paperId}/pdf/fetch`, { method: 'POST' }))
}

// @doc: docs/design/Reader.md#5-api
export async function uploadPdf(paperId: number, file: Blob): Promise<PaperPdf> {
  return pdfResponse(
    await fetch(`/api/papers/${paperId}/pdf`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/pdf' },
      body: file,
    }),
  )
}

// @doc: docs/design/Reader.md#5-api
export interface ReadingPosition {
  page: number
  offset: number
  zoom: number
}

// @doc: docs/design/Reader.md#5-api
export async function fetchPosition(paperId: number): Promise<ReadingPosition | null> {
  const response = await fetch(`/api/papers/${paperId}/position`)
  if (response.status === 204) return null
  if (!response.ok) {
    throw new Error(`읽던 위치 불러오기 실패: ${response.status}`)
  }
  const body = await response.json()
  return { page: body.page, offset: body.offset, zoom: body.zoom }
}

// @doc: docs/design/Reader.md#5-api
export async function savePosition(paperId: number, position: ReadingPosition): Promise<void> {
  const response = await fetch(`/api/papers/${paperId}/position`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(position),
  })
  if (!response.ok) {
    throw new Error(`읽던 위치 저장 실패: ${response.status}`)
  }
}

// @doc: docs/design/Reader.md#5-api
export interface Annotation {
  id: number
  paper_id: number
  kind: 'highlight' | 'note'
  page: number
  rects: { x: number; y: number; w: number; h: number }[]
  text: string | null
  color: string
  note: string | null
  created_at: string
  updated_at: string
}

// @doc: docs/design/Reader.md#5-api
export interface AnnotationInput {
  kind: 'highlight' | 'note'
  page: number
  rects: { x: number; y: number; w: number; h: number }[]
  text?: string | null
  color?: string
  note?: string | null
}

async function annotationResponse<T>(response: Response, what: string): Promise<T> {
  if (!response.ok) {
    throw new Error(`${what} 실패: ${response.status}`)
  }
  return (await response.json()) as T
}

// @doc: docs/design/Reader.md#5-api
export async function listAnnotations(paperId: number): Promise<Annotation[]> {
  return annotationResponse(await fetch(`/api/papers/${paperId}/annotations`), '주석 불러오기')
}

// @doc: docs/design/Reader.md#5-api
export async function createAnnotation(paperId: number, input: AnnotationInput): Promise<Annotation> {
  return annotationResponse(
    await fetch(`/api/papers/${paperId}/annotations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    }),
    '주석 저장',
  )
}

// @doc: docs/design/Reader.md#5-api
export async function updateAnnotation(
  annotationId: number,
  change: { color?: string; note?: string | null },
): Promise<Annotation> {
  return annotationResponse(
    await fetch(`/api/annotations/${annotationId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(change),
    }),
    '주석 고치기',
  )
}

// @doc: docs/design/Reader.md#5-api
export async function deleteAnnotation(annotationId: number): Promise<void> {
  const response = await fetch(`/api/annotations/${annotationId}`, { method: 'DELETE' })
  if (!response.ok) {
    throw new Error(`주석 지우기 실패: ${response.status}`)
  }
}

// @doc: docs/design/Citations.md#6-api와-화면
export interface CitedWork {
  openalex_id: string
  title: string | null
  authors: string[]
  item_type: string
  year: number | null
  venue: string | null
  doi: string | null
  cited_by_count: number | null
  shared_refs: number | null
  library_paper_id: number | null
}

// @doc: docs/design/Citations.md#6-api와-화면
export interface PaperCitations {
  state: 'no_doi' | 'not_found' | 'pending' | 'ready'
  openalex_id: string | null
  fetched_at: string | null
  window_start: string | null
  window_end: string | null
  citing_total: number
  citing_limit: number | null
  references: CitedWork[]
  citations: CitedWork[]
}

// @doc: docs/design/Citations.md#6-api와-화면
export async function fetchPaperCitations(paperId: number): Promise<PaperCitations> {
  const response = await fetch(`/api/papers/${paperId}/citations`)
  if (!response.ok) {
    throw new Error(`인용 목록 불러오기 실패: ${response.status}`)
  }
  return (await response.json()) as PaperCitations
}

// @doc: docs/design/Citations.md#6-api와-화면
export type Direction = 'prior' | 'later'

// @doc: docs/design/Citations.md#6-api와-화면
export type DirectionBasis = 'citation' | 'date'

// @doc: docs/design/Citations.md#6-api와-화면
export interface RelatedWork extends CitedWork {
  score: number
  cites_paper: boolean
  cited_by_paper: boolean
  cocited: number
  direction: Direction | null
  direction_basis: DirectionBasis | null
}

// @doc: docs/design/Citations.md#6-api와-화면
export interface PaperRelated {
  state: PaperCitations['state']
  citing_count: number
  reference_count: number
  works: RelatedWork[]
}

// @doc: docs/design/Citations.md#6-api와-화면
export async function fetchPaperRelated(paperId: number): Promise<PaperRelated> {
  const response = await fetch(`/api/papers/${paperId}/related`)
  if (!response.ok) {
    throw new Error(`가까운 논문 불러오기 실패: ${response.status}`)
  }
  return (await response.json()) as PaperRelated
}

// @doc: docs/design/Citations.md#6-api와-화면
export interface RecommendedWork extends CitedWork {
  score: number
  sources: { paper_id: number; title: string; direction: Direction | null; direction_basis: DirectionBasis | null }[]
  direction: Direction | 'mixed' | null
}

// @doc: docs/design/Citations.md#6-api와-화면
export interface Recommendations {
  papers: number
  papers_used: number
  works: RecommendedWork[]
}

// @doc: docs/design/Citations.md#6-api와-화면
export async function fetchRecommendations(): Promise<Recommendations> {
  const response = await fetch('/api/citations/recommendations')
  if (!response.ok) {
    throw new Error(`추천 불러오기 실패: ${response.status}`)
  }
  return (await response.json()) as Recommendations
}

// @doc: docs/design/CitationGraph.md#4-화면
export interface GraphNode {
  id: string
  paper_id: number | null
  openalex_id: string | null
  title: string
  item_type: string
  authors: string[]
  year: number | null
  venue: string | null
  doi: string | null
  cited_by_count: number | null
  has_data: boolean
  score: number | null
}

// @doc: docs/design/CitationGraph.md#4-화면
export interface GraphEdge {
  source: string
  target: string
  kind: 'cites' | 'related'
  shared_refs: number
  cocited: number
}

// @doc: docs/design/CitationGraph.md#4-화면
export interface CitationGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// @doc: docs/design/CitationGraph.md#4-화면
export async function fetchCitationGraph(outside = 0): Promise<CitationGraph> {
  const response = await fetch(`/api/citations/graph?outside=${outside}`)
  if (!response.ok) {
    throw new Error(`인용 그래프 불러오기 실패: ${response.status}`)
  }
  return (await response.json()) as CitationGraph
}

// @doc: docs/design/ReaderCitations.md#4-논문-찾기
export interface ReferenceMatch {
  state: 'found' | 'not_found'
  source: 'references' | 'search' | null
  work: CitedWork | null
  has_pdf: boolean
  pdf_url: string | null
}

// @doc: docs/design/ReaderCitations.md#4-논문-찾기
export async function resolveReference(paperId: number, text: string): Promise<ReferenceMatch> {
  const response = await fetch(`/api/papers/${paperId}/references/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!response.ok) {
    let detail = ''
    try {
      const body = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : ''
    } catch {
      detail = ''
    }
    throw new Error(detail || `참고문헌 찾기 실패: ${response.status}`)
  }
  return (await response.json()) as ReferenceMatch
}
