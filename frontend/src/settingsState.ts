// @doc: docs/design/Settings.md#4-화면

import { computed, reactive } from 'vue'
import { fetchSettings, saveSettings, type Setting } from './api'

// @doc: docs/design/Settings.md#4-화면
export function createSettingsState(deps = { fetchSettings, saveSettings }) {
  const state = reactive({
    items: [] as Setting[],
    draft: {} as Record<string, number | null>,
    loading: false,
    saving: false,
    error: '',
    message: '',
  })

  const changes = computed(() => {
    const result: Record<string, number> = {}
    for (const item of state.items) {
      const value = state.draft[item.key]
      if (value !== null && value !== undefined && value !== item.value) result[item.key] = value
    }
    return result
  })
  const dirty = computed(() => Object.keys(changes.value).length > 0)

  function apply(items: Setting[]): void {
    state.items = items
    state.draft = Object.fromEntries(items.map((item) => [item.key, item.value]))
  }

  async function load(): Promise<void> {
    state.loading = true
    state.error = ''
    state.message = ''
    try {
      apply(await deps.fetchSettings())
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
    } finally {
      state.loading = false
    }
  }

  async function save(): Promise<void> {
    if (!dirty.value) return
    state.saving = true
    state.error = ''
    state.message = ''
    try {
      apply(await deps.saveSettings(changes.value))
      state.message = '저장했습니다.'
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
    } finally {
      state.saving = false
    }
  }

  function resetToDefault(key: string): void {
    const item = state.items.find((candidate) => candidate.key === key)
    if (item) state.draft[key] = item.default
    state.message = ''
  }

  return { state, changes, dirty, load, save, resetToDefault }
}
