// @doc: docs/design/Auth.md#6-화면

import { computed, reactive } from 'vue'

// @doc: docs/design/Auth.md#6-화면
export interface Me {
  enabled: boolean
  email: string | null
}

// @doc: docs/design/Auth.md#6-화면
export async function fetchMe(): Promise<Me> {
  const response = await fetch('/api/auth/me')
  if (!response.ok) {
    throw new Error(`로그인 상태 확인 실패: ${response.status}`)
  }
  return (await response.json()) as Me
}

// @doc: docs/design/Auth.md#6-화면
export async function logout(): Promise<Me> {
  const response = await fetch('/api/auth/logout', { method: 'POST' })
  if (!response.ok) {
    throw new Error(`로그아웃 실패: ${response.status}`)
  }
  return (await response.json()) as Me
}

// @doc: docs/design/Auth.md#6-화면
export function loginUrl(returnTo: string): string {
  return `/api/auth/login?${new URLSearchParams({ return_to: returnTo })}`
}

// @doc: docs/design/Auth.md#6-화면
export function createAuthState(deps = { fetchMe, logout }) {
  const state = reactive({
    me: null as Me | null,
    error: '',
  })
  const needsLogin = computed(() => state.me !== null && state.me.enabled && state.me.email === null)

  async function refresh(): Promise<void> {
    try {
      state.me = await deps.fetchMe()
      state.error = ''
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
    }
  }

  async function signOut(): Promise<void> {
    try {
      state.me = await deps.logout()
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
    }
  }

  return { state, needsLogin, refresh, signOut }
}

// @doc: docs/design/Auth.md#6-화면
export function watchUnauthorized(
  onUnauthorized: () => void,
  target: { fetch: typeof fetch } = window,
): void {
  const original = target.fetch.bind(target)
  target.fetch = async (input, init) => {
    const response = await original(input, init)
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    if (response.status === 401 && url.includes('/api/') && !url.includes('/api/auth/')) {
      onUnauthorized()
    }
    return response
  }
}
