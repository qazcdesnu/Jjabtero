// @doc: docs/design/ReaderCitations.md#6-테스트

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DuplicatePaperError, type CitedWork, type ReferenceMatch } from './api'
import { CLOSE_DELAY_MS, HOVER_DELAY_MS, createReferencePreview, readTarget } from './referencePreview'

const work: CitedWork = {
  openalex_id: 'W1',
  title: 'Long Short-Term Memory',
  authors: ['Sepp Hochreiter'],
  item_type: 'article',
  year: 1997,
  venue: 'Neural Computation',
  doi: '10.1162/neco.1997.9.8.1735',
  cited_by_count: 100000,
  shared_refs: null,
  library_paper_id: null,
}
const place = { left: 10, top: 20, above: false }

function match(overrides: Partial<ReferenceMatch> = {}): ReferenceMatch {
  return { state: 'found', source: 'references', work: { ...work }, has_pdf: false, pdf_url: 'https://example.org/a.pdf', ...overrides }
}

function setup(overrides = {}, result = match()) {
  const onAdded = vi.fn()
  const entryText = vi.fn().mockResolvedValue('[13] Hochreiter. Long short-term memory. 1997.')
  const deps = {
    resolveReference: vi.fn().mockResolvedValue(result),
    addPaper: vi.fn().mockResolvedValue({ id: 7 }),
    fetchOpenPdf: vi.fn().mockResolvedValue({}),
    ...overrides,
  }
  return { preview: createReferencePreview(3, entryText, onAdded, deps), deps, entryText, onAdded }
}

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('readTarget', () => {
  it('서재 PDF, 공개 PDF, DOI, OpenAlex 순서로 고른다', () => {
    expect(readTarget(match({ has_pdf: true, work: { ...work, library_paper_id: 5 } }))).toEqual({ url: '/api/papers/5/pdf', label: '새 탭에서 읽기' })
    expect(readTarget(match())).toEqual({ url: 'https://example.org/a.pdf', label: '새 탭에서 읽기' })
    expect(readTarget(match({ pdf_url: null }))?.label).toBe('원문 페이지 열기')
    expect(readTarget(match({ pdf_url: null, work: { ...work, doi: null } }))?.url).toBe('https://openalex.org/W1')
    expect(readTarget(match({ state: 'not_found', work: null }))).toBeNull()
  })
})

describe('createReferencePreview', () => {
  it('1초 머물러야 띄우고, 그 전에 벗어나면 띄우지 않는다', async () => {
    const { preview, deps } = setup()
    preview.hover('cite.a', place)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS - 1)
    preview.leave()
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    expect(preview.state.open).toBe(false)
    expect(deps.resolveReference).not.toHaveBeenCalled()

    preview.hover('cite.a', place)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    expect(preview.state.open).toBe(true)
    expect(preview.state.result?.work?.title).toBe('Long Short-Term Memory')
    expect(deps.resolveReference).toHaveBeenCalledWith(3, '[13] Hochreiter. Long short-term memory. 1997.')
  })

  it('링크에서 상자로 옮겨 가면 열려 있고, 둘 다 벗어나면 0.3초 뒤 닫히며, 같은 링크는 다시 찾지 않는다', async () => {
    const { preview, deps, entryText } = setup()
    preview.hover('cite.a', place)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    preview.leave()
    preview.enterBox()
    await vi.advanceTimersByTimeAsync(CLOSE_DELAY_MS * 2)
    expect(preview.state.open).toBe(true)
    preview.leaveBox()
    await vi.advanceTimersByTimeAsync(CLOSE_DELAY_MS)
    expect(preview.state.open).toBe(false)
    preview.hover('cite.a', place)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    expect(entryText).toHaveBeenCalledTimes(1)
    expect(deps.resolveReference).toHaveBeenCalledTimes(1)
  })

  it('항목 글을 읽지 못하거나 찾기가 실패하면 까닭을 보이고, 실패는 다시 시도한다', async () => {
    const empty = setup()
    empty.entryText.mockResolvedValue('')
    empty.preview.hover('cite.a', place)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    expect(empty.preview.state.error).toBe('참고문헌 항목을 읽지 못했습니다.')

    const failing = setup({ resolveReference: vi.fn().mockRejectedValueOnce(new Error('OpenAlex 오류')).mockResolvedValue(match()) })
    failing.preview.hover('cite.a', place)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    expect(failing.preview.state.error).toBe('OpenAlex 오류')
    failing.preview.close()
    failing.preview.hover('cite.a', place)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    expect(failing.preview.state.result?.state).toBe('found')
  })

  it('서재에 담고 PDF를 받으며, 서재 목록을 다시 읽게 한다', async () => {
    const { preview, deps, onAdded } = setup()
    preview.hover('cite.a', place)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    await preview.addAndFetch()
    expect(deps.addPaper).toHaveBeenCalledWith(expect.objectContaining({ openalex_id: 'W1', doi: work.doi }))
    expect(deps.fetchOpenPdf).toHaveBeenCalledWith(7)
    expect(preview.state.result?.work?.library_paper_id).toBe(7)
    expect(preview.state.result?.has_pdf).toBe(true)
    expect(preview.state.message).toBe('서재에 담고 PDF를 받았습니다.')
    expect(onAdded).toHaveBeenCalled()
  })

  it('이미 서재에 있으면 그 논문에 PDF만 받고, PDF를 못 받으면 서재에만 담았다고 알린다', async () => {
    const { preview, deps } = setup({
      addPaper: vi.fn().mockRejectedValue(new DuplicatePaperError(4)),
      fetchOpenPdf: vi.fn().mockRejectedValue(new Error('공개된 PDF를 찾지 못했습니다.')),
    })
    preview.hover('cite.a', place)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    await preview.addAndFetch()
    expect(deps.fetchOpenPdf).toHaveBeenCalledWith(4)
    expect(preview.state.message).toBe('서재에 담았습니다. PDF는 받지 못했습니다: 공개된 PDF를 찾지 못했습니다.')
    expect(preview.state.working).toBe(false)
  })
})
