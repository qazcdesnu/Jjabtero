// @doc: docs/design/Settings.md#5-테스트

import { describe, expect, it, vi } from 'vitest'
import type { Setting } from './api'
import { createSettingsState } from './settingsState'

const item: Setting = {
  key: 'citing_limit',
  label: '가져올 피인용 수',
  description: '설명',
  value: 10,
  default: 10,
  minimum: 1,
  maximum: 1000,
}

function setup(overrides: Partial<Parameters<typeof createSettingsState>[0]> = {}) {
  const deps = {
    fetchSettings: vi.fn().mockResolvedValue([item]),
    saveSettings: vi.fn().mockImplementation(async (changes: Record<string, number>) => [
      { ...item, value: changes.citing_limit ?? item.value },
    ]),
    ...overrides,
  }
  return { settings: createSettingsState(deps), deps }
}

describe('createSettingsState', () => {
  it('불러오면 항목과 입력 값을 채운다', async () => {
    const { settings } = setup()
    await settings.load()
    expect(settings.state.items).toEqual([item])
    expect(settings.state.draft).toEqual({ citing_limit: 10 })
    expect(settings.dirty.value).toBe(false)
  })

  it('바뀐 항목만 보내고 저장했다고 알린다', async () => {
    const { settings, deps } = setup()
    await settings.load()
    settings.state.draft.citing_limit = 30

    await settings.save()

    expect(deps.saveSettings).toHaveBeenCalledWith({ citing_limit: 30 })
    expect(settings.state.items[0].value).toBe(30)
    expect(settings.state.message).toBe('저장했습니다.')
    expect(settings.dirty.value).toBe(false)
  })

  it('바뀐 것이 없거나 입력이 비면 보내지 않는다', async () => {
    const { settings, deps } = setup()
    await settings.load()
    await settings.save()
    settings.state.draft.citing_limit = null
    await settings.save()
    expect(deps.saveSettings).not.toHaveBeenCalled()
  })

  it('기본값으로 누르면 입력 칸만 기본값으로 바꾼다', async () => {
    const { settings, deps } = setup({ fetchSettings: vi.fn().mockResolvedValue([{ ...item, value: 50 }]) })
    await settings.load()
    settings.resetToDefault('citing_limit')
    expect(settings.state.draft.citing_limit).toBe(10)
    expect(settings.changes.value).toEqual({ citing_limit: 10 })
    expect(deps.saveSettings).not.toHaveBeenCalled()
  })

  it('저장이 거절되면 이유를 보여 준다', async () => {
    const { settings } = setup({ saveSettings: vi.fn().mockRejectedValue(new Error('범위를 벗어났습니다')) })
    await settings.load()
    settings.state.draft.citing_limit = 5000
    await settings.save()
    expect(settings.state.error).toBe('범위를 벗어났습니다')
    expect(settings.state.message).toBe('')
  })
})
