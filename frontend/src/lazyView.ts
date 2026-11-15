// @doc: docs/design/UiLayout.md#5-나중에-불러오는-화면

import { defineAsyncComponent, type AsyncComponentLoader } from 'vue'
import LoadFailedView from './LoadFailedView.vue'

// @doc: docs/design/UiLayout.md#5-나중에-불러오는-화면
export const RELOAD_KEY = 'jjabtero:view-reload-at'

// @doc: docs/design/UiLayout.md#5-나중에-불러오는-화면
export const RELOAD_GUARD_MS = 60_000

type ReloadDeps = {
  storage: Pick<Storage, 'getItem' | 'setItem'> | null
  now: () => number
  reload: () => void
}

function sessionStore(): Pick<Storage, 'getItem' | 'setItem'> | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

const defaultDeps: ReloadDeps = {
  storage: sessionStore(),
  now: () => Date.now(),
  reload: () => window.location.reload(),
}

// @doc: docs/design/UiLayout.md#5-나중에-불러오는-화면
export function shouldReload(storage: ReloadDeps['storage'], now: number): boolean {
  // 기록할 곳이 없으면 새로고침이 끝없이 되풀이될 수 있으므로 하지 않는다.
  if (!storage) return false
  try {
    const last = Number(storage.getItem(RELOAD_KEY) ?? 0)
    if (now - last < RELOAD_GUARD_MS) return false
    storage.setItem(RELOAD_KEY, String(now))
    return true
  } catch {
    return false
  }
}

// @doc: docs/design/UiLayout.md#5-나중에-불러오는-화면
export function reloadingLoader<T>(loader: () => Promise<T>, deps: ReloadDeps = defaultDeps): () => Promise<T> {
  return () =>
    loader().catch((error: unknown) => {
      if (shouldReload(deps.storage, deps.now())) deps.reload()
      throw error
    })
}

// @doc: docs/design/UiLayout.md#5-나중에-불러오는-화면
export function lazyView(loader: AsyncComponentLoader) {
  return defineAsyncComponent({ loader: reloadingLoader(loader), errorComponent: LoadFailedView })
}
