<!-- @doc: docs/design/LibraryView.md#3-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import ConfirmPopup from 'primevue/confirmpopup'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { computed, ref } from 'vue'
import { ITEM_TYPE_LABELS, formatDate } from './labels'
import { createLibraryState } from './libraryState'

const props = defineProps<{ library: ReturnType<typeof createLibraryState> }>()
const paper = computed(() => props.library.selected.value)
const removing = ref(false)
const confirm = useConfirm()

function askRemove(event: Event) {
  const target = paper.value
  if (!target) return
  confirm.require({
    target: event.currentTarget as HTMLElement,
    message: '이 논문을 서재에서 지울까요?',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: '취소', severity: 'secondary', outlined: true },
    acceptProps: { label: '삭제', severity: 'danger' },
    accept: async () => {
      removing.value = true
      try {
        await props.library.remove(target)
      } finally {
        removing.value = false
      }
    },
  })
}
</script>

<template>
  <div v-if="paper" class="flex flex-col gap-4 p-4">
    <div class="flex flex-col gap-1">
      <div>
        <Tag :value="ITEM_TYPE_LABELS[paper.item_type] ?? paper.item_type" severity="secondary" />
      </div>
      <h2 class="text-lg leading-snug font-semibold">{{ paper.title }}</h2>
      <p class="text-sm text-surface-600 dark:text-surface-300">
        {{ paper.authors.join(', ') || '저자 정보 없음' }}
      </p>
    </div>

    <dl class="grid grid-cols-[5rem_1fr] gap-x-3 gap-y-2 text-sm">
      <dt class="text-surface-500">연도</dt>
      <dd>{{ paper.year ?? '—' }}</dd>
      <dt class="text-surface-500">게재처</dt>
      <dd>{{ paper.venue ?? '—' }}</dd>
      <dt class="text-surface-500">DOI</dt>
      <dd class="break-all">
        <a v-if="paper.doi" :href="`https://doi.org/${paper.doi}`" target="_blank" rel="noopener" class="text-primary hover:underline">{{ paper.doi }}</a>
        <span v-else>—</span>
      </dd>
      <dt class="text-surface-500">원문</dt>
      <dd class="break-all">
        <a v-if="paper.url" :href="paper.url" target="_blank" rel="noopener" class="text-primary hover:underline">{{ paper.url }}</a>
        <span v-else>—</span>
      </dd>
      <dt class="text-surface-500">태그</dt>
      <dd class="flex flex-wrap gap-1">
        <Tag v-for="tag in paper.tags" :key="tag" :value="tag" />
        <span v-if="paper.tags.length === 0">—</span>
      </dd>
      <dt class="text-surface-500">추가일</dt>
      <dd class="tabular-nums">{{ formatDate(paper.created_at) }}</dd>
    </dl>

    <div class="flex flex-col gap-2">
      <ConfirmPopup />
      <Button label="서재에서 삭제" icon="pi pi-trash" severity="danger" outlined :loading="removing" @click="askRemove" />
      <Message v-if="library.state.removeError" severity="error">{{ library.state.removeError }}</Message>
    </div>
  </div>
</template>
