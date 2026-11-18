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
  // @doc: docs/design/Reader.md#6-화면
  pdf_source?: string | null
  pdf_source_url?: string | null
  id: number
  read_status: string
  note: string | null
  created_at: string
  updated_at: string
  // 리더에서 마지막으로 열었거나 읽은 시각. 연 적이 없으면 담은 시각이다
  // @doc: docs/design/Reader.md#5-api
  last_read_at: string
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
export type SearchMode = 'all' | 'title' | 'author'

// @doc: docs/design/PaperSearch.md#4-화면
export async function searchPapers(query: string, sources: string[], mode: SearchMode = 'all'): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, mode })
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
// @doc: docs/design/Tags.md#5-태그별-그래프
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
export function checkDrive(): Promise<DriveStatus> {
  return driveRequest('check', { method: 'POST' })
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
  s2_checked: number
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

// @doc: docs/design/Reader.md#6-화면
export class NoOpenPdfError extends Error {}

// @doc: docs/design/Reader.md#5-api
export interface OpenVersion {
  openalex_id: string
  title: string
  authors: string[]
  year: number | null
  venue: string | null
  pdf_url: string
  similarity: number
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
    if (response.status === 404 && detail.startsWith('공개된 PDF')) throw new NoOpenPdfError(detail)
    throw new Error(detail || `PDF 요청 실패: ${response.status}`)
  }
  return (await response.json()) as PaperPdf
}

function versionQuery(version?: string): string {
  // 판(SHA-256) 질의. 없으면 서버가 지금 판을 쓴다.
  return version ? `?version=${encodeURIComponent(version)}` : ''
}

// @doc: docs/design/Reader.md#5-api
// @doc: docs/design/PdfVersions.md#5-api
export function pdfUrl(paperId: number, version?: string): string {
  return `/api/papers/${paperId}/pdf${versionQuery(version)}`
}

// @doc: docs/design/PdfVersions.md#5-api
export interface SavedPdfVersion {
  sha256: string
  label: string
  source: string
  source_url: string | null
  added_at: string
  selected: boolean
}

// @doc: docs/design/PdfVersions.md#5-api
export interface AvailablePdfVersion {
  key: string
  label: string
  url: string
  date: string | null
  latest: boolean
  saved_sha256: string | null
}

async function versionsResponse<T>(response: Response, action: string): Promise<T> {
  if (!response.ok) {
    let detail = ''
    try {
      const body = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : ''
    } catch {
      detail = ''
    }
    throw new Error(detail || `${action} 실패: ${response.status}`)
  }
  return (await response.json()) as T
}

// @doc: docs/design/PdfVersions.md#5-api
export async function listPdfVersions(paperId: number): Promise<SavedPdfVersion[]> {
  return versionsResponse(await fetch(`/api/papers/${paperId}/pdf/versions`), '받은 판 불러오기')
}

// @doc: docs/design/PdfVersions.md#5-api
export async function listAvailablePdfVersions(paperId: number): Promise<AvailablePdfVersion[]> {
  return versionsResponse(await fetch(`/api/papers/${paperId}/pdf/versions/available`), '받을 수 있는 판 찾기')
}

// @doc: docs/design/PdfVersions.md#5-api
export async function fetchPdfVersion(paperId: number, key: string): Promise<PaperPdf> {
  return pdfResponse(
    await fetch(`/api/papers/${paperId}/pdf/fetch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ version: key }),
    }),
  )
}

// @doc: docs/design/PdfVersions.md#5-api
export async function selectPdfVersion(paperId: number, sha256: string): Promise<SavedPdfVersion[]> {
  return versionsResponse(
    await fetch(`/api/papers/${paperId}/pdf/selected`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sha256 }),
    }),
    '판 고르기',
  )
}

// @doc: docs/design/Reader.md#5-api
export async function fetchOpenPdf(paperId: number, openalexId?: string): Promise<PaperPdf> {
  // openalexId를 주면 그 공개판의 PDF를 받는다.
  const init: RequestInit = openalexId
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ openalex_id: openalexId }) }
    : { method: 'POST' }
  return pdfResponse(await fetch(`/api/papers/${paperId}/pdf/fetch`, init))
}

// @doc: docs/design/Reader.md#6-화면
export async function fetchPdfAlternatives(paperId: number): Promise<OpenVersion[]> {
  const response = await fetch(`/api/papers/${paperId}/pdf/alternatives`)
  if (!response.ok) throw new Error(`비슷한 공개판을 찾지 못했습니다: ${response.status}`)
  return (await response.json()) as OpenVersion[]
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
export async function fetchPosition(paperId: number, version?: string): Promise<ReadingPosition | null> {
  const response = await fetch(`/api/papers/${paperId}/position${versionQuery(version)}`)
  if (response.status === 204) return null
  if (!response.ok) {
    throw new Error(`읽던 위치 불러오기 실패: ${response.status}`)
  }
  const body = await response.json()
  return { page: body.page, offset: body.offset, zoom: body.zoom }
}

// @doc: docs/design/Reader.md#5-api
export async function savePosition(paperId: number, position: ReadingPosition, version?: string): Promise<void> {
  const response = await fetch(`/api/papers/${paperId}/position${versionQuery(version)}`, {
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
export async function listAnnotations(paperId: number, version?: string): Promise<Annotation[]> {
  return annotationResponse(await fetch(`/api/papers/${paperId}/annotations${versionQuery(version)}`), '주석 불러오기')
}

// @doc: docs/design/Reader.md#5-api
export async function createAnnotation(paperId: number, input: AnnotationInput, version?: string): Promise<Annotation> {
  return annotationResponse(
    await fetch(`/api/papers/${paperId}/annotations${versionQuery(version)}`, {
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
  date: string | null
  date_precision: 'day' | 'month' | 'year' | null
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
// @doc: docs/design/Tags.md#5-태그별-그래프
export async function fetchCitationGraph(outside = 0, tags: string[] = []): Promise<CitationGraph> {
  const params = new URLSearchParams({ outside: String(outside) })
  for (const tag of tags) params.append('tags', tag)
  const response = await fetch(`/api/citations/graph?${params}`)
  if (!response.ok) {
    throw new Error(`인용 그래프 불러오기 실패: ${response.status}`)
  }
  return (await response.json()) as CitationGraph
}

// @doc: docs/design/ReaderCitations.md#4-논문-찾기
export interface ReferenceMatch {
  state: 'found' | 'not_found'
  source: 'identifier' | 'references' | 'search' | null
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

async function tagRequest<T>(url: string, init: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json' } })
  if (!response.ok) {
    let detail = ''
    try {
      const body = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : ''
    } catch {
      detail = ''
    }
    throw new Error(detail || `태그 저장 실패: ${response.status}`)
  }
  return (await response.json()) as T
}

// @doc: docs/design/Tags.md#4-화면
export function setPaperTags(paperId: number, tags: string[]): Promise<Paper> {
  return tagRequest<Paper>(`/api/papers/${paperId}/tags`, { method: 'PUT', body: JSON.stringify({ tags }) })
}

// @doc: docs/design/Tags.md#4-화면
export async function applyTags(paperIds: number[], add: string[], remove: string[]): Promise<number> {
  const body = { paper_ids: paperIds, add, remove }
  return (await tagRequest<{ changed: number }>('/api/tags/apply', { method: 'POST', body: JSON.stringify(body) })).changed
}

// @doc: docs/design/Tags.md#4-화면
export async function renameTag(name: string, newName: string): Promise<number> {
  const url = `/api/tags/${encodeURIComponent(name)}`
  return (await tagRequest<{ changed: number }>(url, { method: 'PATCH', body: JSON.stringify({ name: newName }) })).changed
}

// @doc: docs/design/Tags.md#4-화면
export async function deleteTag(name: string): Promise<number> {
  return (await tagRequest<{ changed: number }>(`/api/tags/${encodeURIComponent(name)}`, { method: 'DELETE' })).changed
}

// @doc: docs/design/AiChat.md#5-api
export interface AiKeyStatus {
  registered: boolean
  hint: string | null
  usable: boolean
  master_key: boolean
  model: string | null
}

// @doc: docs/design/AiChat.md#5-api
export interface AiModel {
  name: string
  label: string
  description: string
}

// 고를 수 있는 모델(오늘 무료 등급)과 무료 목록을 읽은 시각. stale이면 지난 목록이다
// @doc: docs/design/AiChat.md#5-api
export interface AiModelList {
  models: AiModel[]
  checked_at: string
  stale: boolean
}

// @doc: docs/design/AiChat.md#5-api
async function aiRequest<T>(url: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json' } })
  if (!response.ok) {
    let detail = ''
    try {
      const body = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : ''
    } catch {
      detail = ''
    }
    throw new Error(detail || `AI 요청 실패: ${response.status}`)
  }
  return (await response.json()) as T
}

// @doc: docs/design/AiChat.md#6-화면
export function fetchAiKey(): Promise<AiKeyStatus> {
  return aiRequest<AiKeyStatus>('/api/ai/key')
}

// @doc: docs/design/AiChat.md#6-화면
export function saveAiKey(apiKey: string): Promise<AiKeyStatus> {
  return aiRequest<AiKeyStatus>('/api/ai/key', { method: 'PUT', body: JSON.stringify({ api_key: apiKey }) })
}

// @doc: docs/design/AiChat.md#6-화면
export function deleteAiKey(): Promise<AiKeyStatus> {
  return aiRequest<AiKeyStatus>('/api/ai/key', { method: 'DELETE' })
}

// @doc: docs/design/AiChat.md#6-화면
export function fetchAiModels(): Promise<AiModelList> {
  return aiRequest<AiModelList>('/api/ai/models')
}

// @doc: docs/design/AiChat.md#6-화면
export function chooseAiModel(model: string): Promise<AiKeyStatus> {
  return aiRequest<AiKeyStatus>('/api/ai/model', { method: 'PUT', body: JSON.stringify({ model }) })
}

// @doc: docs/design/AiChat.md#5-api
export interface AiChatMessage {
  role: 'user' | 'model'
  text: string
}

// @doc: docs/design/AiChat.md#6-화면
export function chatAi(
  paperId: number,
  page: number | null,
  context: string,
  messages: AiChatMessage[],
): Promise<{ text: string; model: string }> {
  const body = { paper_id: paperId, page, context, messages }
  return aiRequest<{ text: string; model: string }>('/api/ai/chat', { method: 'POST', body: JSON.stringify(body) })
}
