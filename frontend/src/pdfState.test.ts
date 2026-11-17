// @doc: docs/design/Reader.md#8-테스트

import { describe, expect, it, vi } from 'vitest'
import { NoOpenPdfError, type OpenVersion } from './api'
import { createPdfState } from './pdfState'

function setup(overrides = {}) {
  const onChanged = vi.fn()
  const deps = {
    fetchOpenPdf: vi.fn().mockResolvedValue({}),
    uploadPdf: vi.fn().mockResolvedValue({}),
    fetchPdfAlternatives: vi.fn().mockResolvedValue([]),
    ...overrides,
  }
  return { pdf: createPdfState(onChanged, deps), deps, onChanged }
}

describe('createPdfState', () => {
  it('공개 PDF를 받으면 알리고 목록을 다시 읽게 한다', async () => {
    const { pdf, deps, onChanged } = setup()
    await expect(pdf.fetchOpen(3)).resolves.toBe(true)
    expect(deps.fetchOpenPdf).toHaveBeenCalledWith(3)
    expect(pdf.state.message).toBe('PDF를 받았습니다.')
    expect(onChanged).toHaveBeenCalled()
  })

  it('올리면 파일을 보낸다', async () => {
    const { pdf, deps } = setup()
    const file = new Blob(['%PDF-'])
    await pdf.upload(3, file)
    expect(deps.uploadPdf).toHaveBeenCalledWith(3, file)
    expect(pdf.state.message).toBe('PDF를 올렸습니다.')
  })

  it('실패하면 서버가 준 이유를 보여 주고 목록을 다시 읽지 않는다', async () => {
    const { pdf, onChanged } = setup({ fetchOpenPdf: vi.fn().mockRejectedValue(new Error('공개된 PDF를 찾지 못했습니다.')) })
    await expect(pdf.fetchOpen(3)).resolves.toBe(false)
    expect(pdf.state.error).toBe('공개된 PDF를 찾지 못했습니다.')
    expect(pdf.state.busy).toBe(false)
    expect(onChanged).not.toHaveBeenCalled()
  })

  it('공개 PDF가 없으면 비슷한 공개판을 찾아 묻고, 고르면 그 공개판으로 받는다', async () => {
    const version: OpenVersion = { openalex_id: 'W2', title: 'Goedel Machines', authors: ['J'], year: 2003, venue: 'arXiv', pdf_url: 'u', similarity: 0.97 }
    const fetchOpenPdf = vi.fn().mockRejectedValueOnce(new NoOpenPdfError('공개된 PDF를 찾지 못했습니다.')).mockResolvedValue({})
    const { pdf, deps, onChanged } = setup({ fetchOpenPdf, fetchPdfAlternatives: vi.fn().mockResolvedValue([version]) })
    await expect(pdf.fetchOpen(3)).resolves.toBe(false)
    expect(deps.fetchPdfAlternatives).toHaveBeenCalledWith(3)
    expect(pdf.state.alternatives).toEqual([version])
    expect(pdf.state.error).toBe('')
    await expect(pdf.fetchAlternative(3, version)).resolves.toBe(true)
    expect(fetchOpenPdf).toHaveBeenLastCalledWith(3, 'W2')
    expect(pdf.state.alternatives).toEqual([])
    expect(pdf.state.message).toBe('비슷한 공개판의 PDF를 받았습니다.')
    expect(onChanged).toHaveBeenCalled()
  })

  it('공개판을 받지 않거나 공개판이 없으면 공개 PDF가 없다고 알리고, 다른 실패에는 공개판을 찾지 않는다', async () => {
    const version = { openalex_id: 'W2' } as OpenVersion
    const missing = setup({
      fetchOpenPdf: vi.fn().mockRejectedValue(new NoOpenPdfError('공개된 PDF를 찾지 못했습니다.')),
      fetchPdfAlternatives: vi.fn().mockResolvedValue([version]),
    })
    await missing.pdf.fetchOpen(3)
    missing.pdf.declineAlternatives()
    expect(missing.pdf.state.alternatives).toEqual([])
    expect(missing.pdf.state.error).toBe('공개된 PDF를 찾지 못했습니다.')

    const none = setup({ fetchOpenPdf: vi.fn().mockRejectedValue(new NoOpenPdfError('없음')) })
    await none.pdf.fetchOpen(3)
    expect(none.pdf.state.error).toBe('없음')

    const broken = setup({ fetchOpenPdf: vi.fn().mockRejectedValue(new Error('PDF를 받지 못했습니다')) })
    await broken.pdf.fetchOpen(3)
    expect(broken.deps.fetchPdfAlternatives).not.toHaveBeenCalled()
  })
})
