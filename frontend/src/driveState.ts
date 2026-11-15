// @doc: docs/design/DriveSync.md#7-화면

import { reactive } from 'vue'
import {
  checkDrive,
  disconnectDrive,
  fetchDriveStatus,
  resolveDrive,
  syncDrive,
  type DriveStatus,
} from './api'

const FAST_POLL_MS = 2000
const SLOW_POLL_MS = 10000
// @doc: docs/design/DriveSync.md#7-화면
export const CHECK_GAP_MS = 15000

// @doc: docs/design/DriveSync.md#7-화면
export function syncedLabel(status: DriveStatus): string {
  if (status.pending) return '올릴 변경 있음'
  if (!status.last_synced_at) return '드라이브 동기화됨'
  const time = new Date(status.last_synced_at)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `드라이브 동기화됨 · ${pad(time.getMonth() + 1)}-${pad(time.getDate())} ${pad(time.getHours())}:${pad(time.getMinutes())}`
}

// @doc: docs/design/DriveSync.md#7-화면
export function createDriveState(
  onDataChanged: () => void,
  deps = { fetchDriveStatus, syncDrive, checkDrive, resolveDrive, disconnectDrive },
) {
  const state = reactive({
    status: null as DriveStatus | null,
    error: '',
    busy: false,
  })
  let lastDataVersion: number | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let running = false

  function apply(status: DriveStatus): void {
    if (lastDataVersion !== null && status.data_version !== lastDataVersion) {
      onDataChanged()
    }
    lastDataVersion = status.data_version
    state.status = status
    state.error = ''
  }

  async function call(action: () => Promise<DriveStatus>): Promise<void> {
    try {
      apply(await action())
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
    }
  }

  function nextDelay(): number {
    const status = state.status
    return status && (status.state === 'syncing' || status.pending) ? FAST_POLL_MS : SLOW_POLL_MS
  }

  async function poll(): Promise<void> {
    await call(deps.fetchDriveStatus)
    if (running) {
      timer = setTimeout(poll, nextDelay())
    }
  }

  async function act(action: () => Promise<DriveStatus>): Promise<void> {
    state.busy = true
    try {
      await call(action)
    } finally {
      state.busy = false
    }
  }

  // 앱 창으로 돌아오면 드라이브를 확인한다. 다른 곳(서버, 다른 컴퓨터)이 그새 올린 변경을 바로 받기 위해서다.
  let lastCheck = 0
  function onVisible(): void {
    if (typeof document === 'undefined' || document.visibilityState !== 'visible' || !state.status) return
    if (!['idle', 'error'].includes(state.status.state) || Date.now() - lastCheck < CHECK_GAP_MS) return
    lastCheck = Date.now()
    void call(deps.checkDrive)
  }

  return {
    state,
    start: async () => {
      running = true
      if (typeof window !== 'undefined') {
        document.addEventListener('visibilitychange', onVisible)
        window.addEventListener('focus', onVisible)
      }
      await poll()
    },
    stop: () => {
      running = false
      if (typeof window !== 'undefined') {
        document.removeEventListener('visibilitychange', onVisible)
        window.removeEventListener('focus', onVisible)
      }
      if (timer !== null) clearTimeout(timer)
      timer = null
    },
    checkNow: onVisible,
    refresh: () => call(deps.fetchDriveStatus),
    syncNow: () => act(deps.syncDrive),
    resolve: (choice: 'remote' | 'local') => act(() => deps.resolveDrive(choice)),
    disconnect: () => act(deps.disconnectDrive),
  }
}
