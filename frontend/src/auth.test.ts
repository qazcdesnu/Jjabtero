// @doc: docs/design/Auth.md#7-테스트

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createAuthState, fetchMe, loginUrl, logout, watchUnauthorized } from './auth'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('로그인 API', () => {
  it('상태를 묻고 로그아웃한다', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(async () => new Response(JSON.stringify({ enabled: true, email: null })))
    vi.stubGlobal('fetch', fetchMock)
    await expect(fetchMe()).resolves.toEqual({ enabled: true, email: null })
    await logout()
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual(['/api/auth/me', '/api/auth/logout'])
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST' })
  })

  it('실패 응답이면 상태 코드를 담은 오류를 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })))
    await expect(fetchMe()).rejects.toThrow('500')
  })

  it('로그인 주소에 돌아올 경로를 담는다', () => {
    expect(loginUrl('/?a=1')).toBe('/api/auth/login?return_to=%2F%3Fa%3D1')
  })
})

describe('createAuthState', () => {
  it('로그인이 켜져 있고 로그인하지 않았을 때만 needsLogin이다', async () => {
    const answers = [
      { enabled: false, email: null },
      { enabled: true, email: null },
      { enabled: true, email: 'me@example.com' },
    ]
    const auth = createAuthState({
      fetchMe: vi.fn(async () => answers.shift()!),
      logout: vi.fn(async () => ({ enabled: true, email: null })),
    })
    expect(auth.needsLogin.value).toBe(false)
    await auth.refresh()
    expect(auth.needsLogin.value).toBe(false)
    await auth.refresh()
    expect(auth.needsLogin.value).toBe(true)
    await auth.refresh()
    expect(auth.needsLogin.value).toBe(false)
    await auth.signOut()
    expect(auth.needsLogin.value).toBe(true)
  })

  it('실패하면 오류를 담는다', async () => {
    const auth = createAuthState({
      fetchMe: vi.fn().mockRejectedValue(new Error('로그인 상태 확인 실패: 500')),
      logout: vi.fn(),
    })
    await auth.refresh()
    expect(auth.state.error).toBe('로그인 상태 확인 실패: 500')
  })
})

describe('watchUnauthorized', () => {
  it('로그인 API 밖의 401에서만 콜백을 부르고 응답은 그대로 돌려준다', async () => {
    const target = {
      fetch: vi.fn(async (input: RequestInfo | URL) =>
        new Response('', { status: String(input).includes('ok') ? 200 : 401 }),
      ) as unknown as typeof fetch,
    }
    const onUnauthorized = vi.fn()
    watchUnauthorized(onUnauthorized, target)
    expect((await target.fetch('/api/papers')).status).toBe(401)
    await target.fetch('/api/auth/me')
    await target.fetch('/api/ok')
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })
})
