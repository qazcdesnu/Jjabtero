<!-- @doc: docs/design/AiChat.md#6-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import { nextTick, ref, watch } from 'vue'
import { QUICK_PROMPTS, type createAiChatState } from './aiChatState'

// chat: 리더가 가진 대화 상태. keyVersion: 프로필에서 키나 모델을 바꿀 때마다 늘어나는 수.
const props = defineProps<{ chat: ReturnType<typeof createAiChatState>; keyVersion: number }>()
const emit = defineEmits<{ profile: [] }>()
const list = ref<HTMLElement | null>(null)

watch(
  () => props.keyVersion,
  () => void props.chat.checkKey(),
)

watch(
  () => [props.chat.state.messages.length, props.chat.state.sending],
  async () => {
    await nextTick()
    list.value?.scrollTo({ top: list.value.scrollHeight })
  },
)

function onKeyDown(event: KeyboardEvent) {
  // 한글 입력을 마치는 Enter는 보내지 않는다. Shift+Enter는 줄바꿈이다.
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  event.preventDefault()
  void props.chat.send(props.chat.state.input)
}
</script>

<template>
  <aside
    v-if="chat.state.context"
    class="flex w-96 shrink-0 flex-col border-l border-surface-200 bg-surface-0 dark:border-surface-700 dark:bg-surface-900"
    aria-label="AI 대화"
  >
    <div class="flex items-center gap-2 border-b border-surface-200 px-3 py-2 dark:border-surface-700">
      <i class="pi pi-sparkles text-primary" />
      <span class="font-medium">AI 대화</span>
      <span v-if="chat.state.model" class="truncate text-xs text-surface-500">{{ chat.state.model }}</span>
      <span class="flex-1" />
      <Button icon="pi pi-times" text rounded size="small" aria-label="AI 대화 닫기" @click="chat.close()" />
    </div>
    <div class="border-b border-surface-200 px-3 py-2 dark:border-surface-700">
      <span v-if="chat.state.context.page" class="text-xs text-surface-500">{{ chat.state.context.page }}쪽에서 고른 글</span>
      <p class="line-clamp-4 text-sm text-surface-600 dark:text-surface-300" :title="chat.state.context.text">
        “{{ chat.state.context.text }}”
      </p>
    </div>

    <div v-if="chat.state.key && !chat.state.key.usable" class="flex flex-col items-start gap-2 p-3">
      <p class="text-sm">
        {{ chat.state.key.registered ? '등록된 API 키를 이곳에서 쓸 수 없습니다.' : 'Gemini와 대화하려면 프로필에서 Google AI API 키를 등록하세요.' }}
      </p>
      <Button label="프로필 열기" icon="pi pi-user" size="small" @click="emit('profile')" />
    </div>
    <template v-else>
      <div ref="list" class="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3">
        <div v-if="chat.state.messages.length === 0" class="flex flex-wrap gap-2">
          <Button
            v-for="prompt in QUICK_PROMPTS"
            :key="prompt.label"
            :label="prompt.label"
            size="small"
            severity="secondary"
            outlined
            :disabled="chat.state.sending"
            @click="chat.send(prompt.text)"
          />
        </div>
        <div
          v-for="(message, index) in chat.state.messages"
          :key="index"
          class="whitespace-pre-wrap break-words rounded-lg px-3 py-2 text-sm"
          :class="message.role === 'user' ? 'self-end bg-primary-50 dark:bg-primary-950' : 'self-start bg-surface-100 dark:bg-surface-800'"
        >{{ message.text }}</div>
        <p v-if="chat.state.sending" class="text-sm text-surface-500"><i class="pi pi-spin pi-spinner mr-1" />답을 기다리는 중…</p>
        <Message v-if="chat.state.error" severity="error" size="small">{{ chat.state.error }}</Message>
      </div>
      <form class="flex items-end gap-2 border-t border-surface-200 p-2 dark:border-surface-700" @submit.prevent="chat.send(chat.state.input)">
        <Textarea
          v-model="chat.state.input"
          rows="2"
          auto-resize
          class="max-h-40 min-w-0 flex-1"
          placeholder="이 글에 대해 묻기 (Enter로 보내기)"
          aria-label="AI에게 물을 말"
          @keydown="onKeyDown"
        />
        <Button type="submit" icon="pi pi-send" aria-label="보내기" :loading="chat.state.sending" :disabled="!chat.state.input.trim()" />
      </form>
    </template>
  </aside>
</template>
