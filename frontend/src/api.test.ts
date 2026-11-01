// @doc: docs/design/AppSkeleton.md#4-테스트

import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchHealth } from './api'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('fetchHealth', () => {
  it('성공 응답이면 상태를 돌려준다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok', version: '0.1.0' }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchHealth()).resolves.toEqual({ status: 'ok', version: '0.1.0' })
    expect(fetchMock).toHaveBeenCalledWith('/api/health')
  })

  it('실패 응답이면 상태 코드를 담은 오류를 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 503 })))

    await expect(fetchHealth()).rejects.toThrow('503')
  })
})
