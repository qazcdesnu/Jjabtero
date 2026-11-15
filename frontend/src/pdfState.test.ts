// @doc: docs/design/Reader.md#8-테스트

import { describe, expect, it, vi } from 'vitest'
import { createPdfState } from './pdfState'

function setup(overrides = {}) {
  const onChanged = vi.fn()
  const deps = {
    fetchOpenPdf: vi.fn().mockResolvedValue({}),
    uploadPdf: vi.fn().mockResolvedValue({}),
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
})
