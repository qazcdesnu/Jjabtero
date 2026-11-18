// @doc: docs/design/AiChat.md#6-화면

import { reactive } from 'vue'
import { chatAi, fetchAiKey, type AiChatMessage, type AiKeyStatus } from './api'

// 빠른 버튼과 그 버튼이 보내는 말
// @doc: docs/design/AiChat.md#6-화면
export const QUICK_PROMPTS = [
  { label: '번역', text: '이 글을 한국어로 번역해 줘. 이미 한국어면 영어로 번역해 줘.' },
  { label: '요약', text: '이 글을 짧게 요약해 줘.' },
  { label: '쉽게 설명', text: '이 글을 배경지식이 없는 사람도 알도록 쉽게 설명해 줘.' },
] as const

// @doc: docs/design/AiChat.md#6-화면
export interface ChatContext {
  text: string
  page: number | null
}

const DEPS = { chatAi, fetchAiKey }

// 리더 대화 칸의 상태. 새 글로 시작하면 지난 대화는 버린다.
// @doc: docs/design/AiChat.md#6-화면
export function createAiChatState(paperId: number, deps = DEPS) {
  const state = reactive({
    context: null as ChatContext | null,
    messages: [] as AiChatMessage[],
    key: null as AiKeyStatus | null,
    model: '',
    input: '',
    sending: false,
    error: '',
  })
  // 늦게 온 답이 새 대화에 섞이지 않게 대화마다 번호를 붙인다.
  let round = 0

  async function checkKey(): Promise<void> {
    try {
      state.key = await deps.fetchAiKey()
      state.model = state.key.model ?? ''
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
    }
  }

  function start(context: ChatContext): void {
    round += 1
    state.context = { text: context.text.trim(), page: context.page }
    state.messages = []
    state.input = ''
    state.error = ''
    state.sending = false
    void checkKey()
  }

  function close(): void {
    round += 1
    state.context = null
    state.messages = []
    state.sending = false
    state.error = ''
  }

  async function send(text: string): Promise<void> {
    const question = text.trim()
    const context = state.context
    if (!question || !context || state.sending) return
    const mine = round
    state.messages = [...state.messages, { role: 'user', text: question }]
    state.input = ''
    state.sending = true
    state.error = ''
    try {
      const answer = await deps.chatAi(paperId, context.page, context.text, state.messages)
      if (mine !== round) return
      state.messages = [...state.messages, { role: 'model', text: answer.text }]
      state.model = answer.model
    } catch (error) {
      if (mine !== round) return
      // 실패한 질문은 빼고 입력 칸에 돌려놓아 다시 보낼 수 있게 한다.
      state.messages = state.messages.slice(0, -1)
      state.input = question
      state.error = error instanceof Error ? error.message : String(error)
    } finally {
      if (mine === round) state.sending = false
    }
  }

  return { state, start, close, send, checkKey }
}
