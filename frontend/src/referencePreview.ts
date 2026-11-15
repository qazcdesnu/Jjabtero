// @doc: docs/design/ReaderCitations.md#5-상자

import { reactive } from 'vue'
import { DuplicatePaperError, addPaper, fetchOpenPdf, pdfUrl, resolveReference, type ReferenceMatch } from './api'
import { citedWorkInput } from './citationListState'

// @doc: docs/design/ReaderCitations.md#5-상자
export const HOVER_DELAY_MS = 1000
// @doc: docs/design/ReaderCitations.md#5-상자
export const CLOSE_DELAY_MS = 300

// @doc: docs/design/ReaderCitations.md#5-상자
export interface PreviewPlace {
  left: number
  top: number
  above: boolean
}

// @doc: docs/design/ReaderCitations.md#5-상자
export function readTarget(match: ReferenceMatch): { url: string; label: string } | null {
  const work = match.work
  if (!work) return null
  if (match.has_pdf && work.library_paper_id) return { url: pdfUrl(work.library_paper_id), label: '새 탭에서 읽기' }
  if (match.pdf_url) return { url: match.pdf_url, label: '새 탭에서 읽기' }
  if (work.doi) return { url: `https://doi.org/${work.doi}`, label: '원문 페이지 열기' }
  return { url: `https://openalex.org/${work.openalex_id}`, label: '원문 페이지 열기' }
}

type Timers = { set: (callback: () => void, ms: number) => unknown; clear: (handle: unknown) => void }

const browserTimers: Timers = {
  set: (callback, ms) => setTimeout(callback, ms),
  clear: (handle) => clearTimeout(handle as ReturnType<typeof setTimeout>),
}

// @doc: docs/design/ReaderCitations.md#5-상자
export function createReferencePreview(
  paperId: number,
  entryText: (dest: string) => Promise<string>,
  onAdded: () => Promise<void> | void,
  deps = { resolveReference, addPaper, fetchOpenPdf },
  timers: Timers = browserTimers,
) {
  const state = reactive({
    open: false,
    dest: '',
    place: { left: 0, top: 0, above: false } as PreviewPlace,
    text: '',
    loading: false,
    result: null as ReferenceMatch | null,
    error: '',
    working: false,
    message: '',
  })
  const results = new Map<string, Promise<{ text: string; match: ReferenceMatch | null }>>()
  let hoverTimer: unknown = null
  let closeTimer: unknown = null
  let hovered = ''
  let token = 0

  function cancel(handle: unknown) {
    if (handle !== null) timers.clear(handle)
  }

  function lookup(dest: string) {
    let found = results.get(dest)
    if (!found) {
      found = (async () => {
        const text = await entryText(dest)
        return { text, match: text ? await deps.resolveReference(paperId, text) : null }
      })()
      // 실패는 기억하지 않아 다음에 다시 찾게 한다.
      found.catch(() => results.delete(dest))
      results.set(dest, found)
    }
    return found
  }

  async function show(dest: string, place: PreviewPlace): Promise<void> {
    const mine = ++token
    Object.assign(state, { open: true, dest, place, text: '', loading: true, result: null, error: '', message: '' })
    try {
      const { text, match } = await lookup(dest)
      if (mine !== token) return
      state.text = text
      state.result = match
      if (!text) state.error = '참고문헌 항목을 읽지 못했습니다.'
    } catch (error) {
      if (mine !== token) return
      state.error = error instanceof Error ? error.message : String(error)
    } finally {
      if (mine === token) state.loading = false
    }
  }

  // 인용 링크 위에 마우스가 들어오면 1초 뒤에 상자를 띄운다.
  function hover(dest: string, place: PreviewPlace): void {
    cancel(closeTimer)
    closeTimer = null
    if (hovered === dest) return
    hovered = dest
    cancel(hoverTimer)
    if (state.open && state.dest === dest) return
    hoverTimer = timers.set(() => {
      hoverTimer = null
      void show(dest, place)
    }, HOVER_DELAY_MS)
  }

  function scheduleClose(): void {
    cancel(closeTimer)
    closeTimer = state.open ? timers.set(close, CLOSE_DELAY_MS) : null
  }

  function leave(): void {
    hovered = ''
    cancel(hoverTimer)
    hoverTimer = null
    scheduleClose()
  }

  function enterBox(): void {
    cancel(closeTimer)
    closeTimer = null
  }

  function close(): void {
    cancel(hoverTimer)
    cancel(closeTimer)
    hoverTimer = closeTimer = null
    hovered = ''
    token += 1
    state.open = false
  }

  // 서재에 없으면 담고, PDF가 없으면 공개 PDF를 받는다.
  async function addAndFetch(): Promise<void> {
    const match = state.result
    const work = match?.work
    if (!match || !work) return
    state.working = true
    state.message = ''
    try {
      let paperId = work.library_paper_id
      if (!paperId) {
        try {
          paperId = (await deps.addPaper(citedWorkInput(work))).id
        } catch (error) {
          if (!(error instanceof DuplicatePaperError)) throw error
          paperId = error.paperId
        }
        work.library_paper_id = paperId
      }
      if (match.has_pdf) {
        state.message = '서재에 담았습니다.'
      } else {
        try {
          await deps.fetchOpenPdf(paperId)
          match.has_pdf = true
          state.message = '서재에 담고 PDF를 받았습니다.'
        } catch (error) {
          state.message = `서재에 담았습니다. PDF는 받지 못했습니다: ${error instanceof Error ? error.message : String(error)}`
        }
      }
      await onAdded()
    } catch (error) {
      state.message = `서재에 담지 못했습니다: ${error instanceof Error ? error.message : String(error)}`
    } finally {
      state.working = false
    }
  }

  return { state, hover, leave, enterBox, leaveBox: scheduleClose, close, addAndFetch }
}
