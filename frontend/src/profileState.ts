// @doc: docs/design/AiChat.md#6-화면

import { reactive } from 'vue'
import { chooseAiModel, deleteAiKey, fetchAiKey, fetchAiModels, saveAiKey, type AiKeyStatus, type AiModel } from './api'

const DEPS = { fetchAiKey, saveAiKey, deleteAiKey, fetchAiModels, chooseAiModel }

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

// 프로필 창의 API 키와 모델 상태. 입력한 키는 등록하면 바로 비운다.
// @doc: docs/design/AiChat.md#6-화면
export function createProfileState(deps = DEPS) {
  const state = reactive({
    status: null as AiKeyStatus | null,
    models: [] as AiModel[],
    keyInput: '',
    editing: false,
    busy: false,
    error: '',
    message: '',
  })

  function begin(): void {
    state.busy = true
    state.error = ''
    state.message = ''
  }

  async function loadModels(): Promise<void> {
    state.models = []
    if (!state.status?.usable) return
    try {
      state.models = await deps.fetchAiModels()
    } catch (error) {
      state.error = message(error)
    }
  }

  async function load(): Promise<void> {
    begin()
    try {
      state.status = await deps.fetchAiKey()
      state.editing = !state.status.registered
      await loadModels()
    } catch (error) {
      state.error = message(error)
    } finally {
      state.busy = false
    }
  }

  async function saveKey(): Promise<void> {
    const key = state.keyInput.trim()
    if (!key) return
    begin()
    try {
      const changed = state.status?.registered
      state.status = await deps.saveAiKey(key)
      state.keyInput = ''
      state.editing = false
      state.message = changed ? 'API 키를 바꿨습니다.' : 'API 키를 등록했습니다.'
      await loadModels()
    } catch (error) {
      state.error = message(error)
    } finally {
      state.busy = false
    }
  }

  async function removeKey(): Promise<void> {
    begin()
    try {
      state.status = await deps.deleteAiKey()
      state.models = []
      state.keyInput = ''
      state.editing = true
      state.message = 'API 키를 지웠습니다.'
    } catch (error) {
      state.error = message(error)
    } finally {
      state.busy = false
    }
  }

  async function chooseModel(model: string): Promise<void> {
    begin()
    try {
      state.status = await deps.chooseAiModel(model)
      state.message = '모델을 바꿨습니다.'
    } catch (error) {
      state.error = message(error)
    } finally {
      state.busy = false
    }
  }

  function startEdit(): void {
    state.editing = true
    state.keyInput = ''
    state.error = ''
    state.message = ''
  }

  function cancelEdit(): void {
    state.editing = !state.status?.registered
    state.keyInput = ''
  }

  return { state, load, saveKey, removeKey, chooseModel, startEdit, cancelEdit }
}
