// @doc: docs/design/AiChat.md#7-테스트

import { describe, expect, it, vi } from 'vitest'
import type { AiKeyStatus, AiModel, AiModelList } from './api'
import { createProfileState } from './profileState'

const none: AiKeyStatus = { registered: false, hint: null, usable: false, master_key: false, model: null }
const saved: AiKeyStatus = { registered: true, hint: '1234', usable: true, master_key: true, model: 'gemini-2.5-flash' }
const models: AiModel[] = [
  { name: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', description: '' },
  { name: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', description: '' },
]
const list: AiModelList = { models, checked_at: '2026-11-19T00:00:05+09:00', stale: false }

function setup(initial: AiKeyStatus, overrides: Partial<Parameters<typeof createProfileState>[0]> = {}) {
  const deps = {
    fetchAiKey: vi.fn().mockResolvedValue(initial),
    saveAiKey: vi.fn().mockImplementation(async (key: string) => ({ ...saved, hint: key.slice(-4) })),
    deleteAiKey: vi.fn().mockResolvedValue({ ...none, master_key: true, model: 'gemini-2.5-flash' }),
    fetchAiModels: vi.fn().mockResolvedValue(list),
    chooseAiModel: vi.fn().mockImplementation(async (model: string) => ({ ...saved, model })),
    ...overrides,
  }
  return { profile: createProfileState(deps), deps }
}

describe('createProfileState', () => {
  it('키가 없으면 입력 칸을 열고 모델은 부르지 않는다', async () => {
    const { profile, deps } = setup(none)
    await profile.load()
    expect(profile.state.editing).toBe(true)
    expect(deps.fetchAiModels).not.toHaveBeenCalled()
  })

  it('등록하면 입력을 비우고 모델 목록을 받는다', async () => {
    const { profile, deps } = setup(none)
    await profile.load()
    profile.state.keyInput = '  AIza-abcd  '
    await profile.saveKey()
    expect(deps.saveAiKey).toHaveBeenCalledWith('AIza-abcd')
    expect(profile.state.keyInput).toBe('')
    expect(profile.state.editing).toBe(false)
    expect(profile.state.message).toBe('API 키를 등록했습니다.')
    expect(profile.state.models).toEqual(models)
    expect(profile.state.modelsCheckedAt).toBe(list.checked_at)
    expect(profile.state.modelsStale).toBe(false)
  })

  it('지난 무료 목록이면 stale을 둔다', async () => {
    const { profile } = setup(saved, { fetchAiModels: vi.fn().mockResolvedValue({ ...list, stale: true }) })
    await profile.load()
    expect(profile.state.modelsStale).toBe(true)
  })

  it('등록된 키를 바꾸고 지운다', async () => {
    const { profile } = setup(saved)
    await profile.load()
    expect(profile.state.editing).toBe(false)
    profile.startEdit()
    profile.state.keyInput = 'AIza-9876'
    await profile.saveKey()
    expect(profile.state.status?.hint).toBe('9876')
    expect(profile.state.message).toBe('API 키를 바꿨습니다.')
    await profile.removeKey()
    expect(profile.state.status?.registered).toBe(false)
    expect(profile.state.models).toEqual([])
    expect(profile.state.editing).toBe(true)
  })

  it('변경을 취소하면 등록된 상태로 돌아간다', async () => {
    const { profile } = setup(saved)
    await profile.load()
    profile.startEdit()
    profile.state.keyInput = 'x'
    profile.cancelEdit()
    expect(profile.state.editing).toBe(false)
    expect(profile.state.keyInput).toBe('')
  })

  it('모델을 고르고, 실패하면 이유를 보인다', async () => {
    const { profile } = setup(saved, { saveAiKey: vi.fn().mockRejectedValue(new Error('구글이 이 키를 받아들이지 않았습니다.')) })
    await profile.load()
    await profile.chooseModel('gemini-2.5-pro')
    expect(profile.state.status?.model).toBe('gemini-2.5-pro')
    profile.startEdit()
    profile.state.keyInput = 'bad'
    await profile.saveKey()
    expect(profile.state.error).toBe('구글이 이 키를 받아들이지 않았습니다.')
    expect(profile.state.keyInput).toBe('bad')
  })
})
