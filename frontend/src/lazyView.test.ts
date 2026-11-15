// @doc: docs/design/UiLayout.md#4-테스트와-확인

import { describe, expect, it, vi } from 'vitest'
import { RELOAD_GUARD_MS, RELOAD_KEY, reloadingLoader, shouldReload } from './lazyView'

function memoryStorage() {
  const data = new Map<string, string>()
  return { getItem: (key: string) => data.get(key) ?? null, setItem: (key: string, value: string) => void data.set(key, value) }
}

describe('shouldReload', () => {
  it('한 번 새로고침하면 1분 동안은 다시 하지 않는다', () => {
    const storage = memoryStorage()
    expect(shouldReload(storage, 1_000_000)).toBe(true)
    expect(storage.getItem(RELOAD_KEY)).toBe('1000000')
    expect(shouldReload(storage, 1_000_000 + RELOAD_GUARD_MS - 1)).toBe(false)
    expect(shouldReload(storage, 1_000_000 + RELOAD_GUARD_MS)).toBe(true)
  })

  it('기록할 곳이 없거나 기록이 실패하면 새로고침하지 않는다', () => {
    expect(shouldReload(null, 1)).toBe(false)
    const broken = { getItem: () => null, setItem: () => { throw new Error('막힘') } }
    expect(shouldReload(broken, 1)).toBe(false)
  })
})

describe('reloadingLoader', () => {
  it('불러오기에 실패하면 한 번 새로고침하고 오류는 그대로 넘긴다', async () => {
    const reload = vi.fn()
    const deps = { storage: memoryStorage(), now: () => 5_000_000, reload }
    const failing = reloadingLoader(() => Promise.reject(new Error('404')), deps)
    await expect(failing()).rejects.toThrow('404')
    await expect(failing()).rejects.toThrow('404')
    expect(reload).toHaveBeenCalledTimes(1)
  })

  it('성공하면 새로고침하지 않는다', async () => {
    const reload = vi.fn()
    const loader = reloadingLoader(() => Promise.resolve('화면'), { storage: memoryStorage(), now: () => 1, reload })
    await expect(loader()).resolves.toBe('화면')
    expect(reload).not.toHaveBeenCalled()
  })
})
