// @doc: docs/design/AiChat.md#7-테스트

import { describe, expect, it, vi } from 'vitest'
import type { AiKeyStatus } from './api'
import { createAiChatState, QUICK_PROMPTS } from './aiChatState'

const key: AiKeyStatus = { registered: true, hint: '1234', usable: true, master_key: true, model: 'gemini-2.5-flash' }

function setup(overrides: Partial<Parameters<typeof createAiChatState>[1]> = {}) {
  const deps = {
    chatAi: vi.fn().mockResolvedValue({ text: '답입니다.', model: 'gemini-2.5-pro' }),
    fetchAiKey: vi.fn().mockResolvedValue(key),
    ...overrides,
  }
  return { chat: createAiChatState(7, deps), deps }
}

describe('createAiChatState', () => {
  it('시작하면 고른 글을 두고 키 상태를 확인한다', async () => {
    const { chat, deps } = setup()
    chat.start({ text: '  We propose X.  ', page: 3 })
    await vi.waitFor(() => expect(chat.state.key).toEqual(key))
    expect(chat.state.context).toEqual({ text: 'We propose X.', page: 3 })
    expect(chat.state.model).toBe('gemini-2.5-flash')
    expect(deps.fetchAiKey).toHaveBeenCalledOnce()
  })

  it('빠른 버튼의 말을 보내고 답을 이어 붙인다', async () => {
    const chatAi = vi.fn().mockResolvedValue({ text: '답입니다.', model: 'gemini-2.5-pro' })
    const { chat } = setup({ chatAi })
    chat.start({ text: 'We propose X.', page: 3 })
    await chat.send(QUICK_PROMPTS[1].text)
    expect(chatAi).toHaveBeenCalledWith(7, 3, 'We propose X.', [{ role: 'user', text: QUICK_PROMPTS[1].text }])
    expect(chat.state.messages.map((message) => message.role)).toEqual(['user', 'model'])
    expect(chat.state.model).toBe('gemini-2.5-pro')
    await chat.send('더 짧게')
    expect(chatAi.mock.calls[1]![3]).toHaveLength(3)
  })

  it('실패하면 질문을 입력 칸에 돌려놓고 이유를 보인다', async () => {
    const { chat } = setup({ chatAi: vi.fn().mockRejectedValue(new Error('Gemini에 연결하지 못했습니다.')) })
    chat.start({ text: 'X', page: null })
    await chat.send('요약')
    expect(chat.state.messages).toEqual([])
    expect(chat.state.input).toBe('요약')
    expect(chat.state.error).toBe('Gemini에 연결하지 못했습니다.')
    expect(chat.state.sending).toBe(false)
  })

  it('새 글로 시작하면 늦게 온 지난 답은 버린다', async () => {
    let resolve: (value: { text: string; model: string }) => void = () => {}
    const { chat } = setup({ chatAi: vi.fn().mockReturnValue(new Promise((done) => (resolve = done))) })
    chat.start({ text: 'A', page: 1 })
    const pending = chat.send('요약')
    chat.start({ text: 'B', page: 2 })
    resolve({ text: '늦은 답', model: 'm' })
    await pending
    expect(chat.state.context?.text).toBe('B')
    expect(chat.state.messages).toEqual([])
    expect(chat.state.sending).toBe(false)
  })
})
