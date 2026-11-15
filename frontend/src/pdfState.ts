// @doc: docs/design/Reader.md#6-화면

import { reactive } from 'vue'
import { fetchOpenPdf, uploadPdf } from './api'

// @doc: docs/design/Reader.md#6-화면
export function createPdfState(onChanged: () => Promise<void> | void, deps = { fetchOpenPdf, uploadPdf }) {
  const state = reactive({ busy: false, error: '', message: '' })

  async function run(action: () => Promise<unknown>, message: string): Promise<boolean> {
    state.busy = true
    state.error = ''
    state.message = ''
    try {
      await action()
      state.message = message
      await onChanged()
      return true
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
      return false
    } finally {
      state.busy = false
    }
  }

  function fetchOpen(paperId: number): Promise<boolean> {
    return run(() => deps.fetchOpenPdf(paperId), 'PDF를 받았습니다.')
  }

  function upload(paperId: number, file: Blob): Promise<boolean> {
    return run(() => deps.uploadPdf(paperId, file), 'PDF를 올렸습니다.')
  }

  function reset(): void {
    state.error = ''
    state.message = ''
  }

  return { state, fetchOpen, upload, reset }
}
