// @doc: docs/design/Reader.md#6-화면

import { reactive } from 'vue'
import { fetchOpenPdf, fetchPdfAlternatives, NoOpenPdfError, uploadPdf, type OpenVersion } from './api'

// @doc: docs/design/Reader.md#6-화면
export function createPdfState(
  onChanged: () => Promise<void> | void,
  deps = { fetchOpenPdf, uploadPdf, fetchPdfAlternatives },
) {
  // alternatives: 공개 PDF가 없을 때 받을지 물을 비슷한 공개판들. noOpenPdf: 그때의 안내(받지 않기를 누르면 오류로 보인다)
  const state = reactive({ busy: false, error: '', message: '', alternatives: [] as OpenVersion[], noOpenPdf: '' })

  async function run(action: () => Promise<unknown>, message: string, onMissing?: (error: NoOpenPdfError) => Promise<void>) {
    state.busy = true
    state.error = ''
    state.message = ''
    state.alternatives = []
    try {
      await action()
      state.message = message
      await onChanged()
      return true
    } catch (error) {
      if (onMissing && error instanceof NoOpenPdfError) await onMissing(error)
      else state.error = error instanceof Error ? error.message : String(error)
      return false
    } finally {
      state.busy = false
    }
  }

  function fetchOpen(paperId: number): Promise<boolean> {
    // 공개 PDF가 없으면 비슷한 공개판을 찾아 받을지 묻는다. 없거나 찾지 못하면 공개 PDF가 없다는 오류를 보인다.
    return run(() => deps.fetchOpenPdf(paperId), 'PDF를 받았습니다.', async (missing) => {
      const found = await deps.fetchPdfAlternatives(paperId).catch(() => [])
      if (found.length === 0) {
        state.error = missing.message
        return
      }
      state.noOpenPdf = missing.message
      state.alternatives = found
    })
  }

  function fetchAlternative(paperId: number, version: OpenVersion): Promise<boolean> {
    return run(() => deps.fetchOpenPdf(paperId, version.openalex_id), '비슷한 공개판의 PDF를 받았습니다.')
  }

  function declineAlternatives(): void {
    state.error = state.noOpenPdf
    state.alternatives = []
  }

  function upload(paperId: number, file: Blob): Promise<boolean> {
    return run(() => deps.uploadPdf(paperId, file), 'PDF를 올렸습니다.')
  }

  function reset(): void {
    state.error = ''
    state.message = ''
    state.alternatives = []
    state.noOpenPdf = ''
  }

  return { state, fetchOpen, fetchAlternative, declineAlternatives, upload, reset }
}
