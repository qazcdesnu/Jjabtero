<!-- @doc: docs/design/LibraryView.md#3-화면 -->
<!-- @doc: docs/design/ReadingStatus.md#3-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import ConfirmPopup from 'primevue/confirmpopup'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { computed, ref, watch } from 'vue'
import { ITEM_TYPE_LABELS, READ_STATUSES, formatDate } from './labels'
import { createLibraryState } from './libraryState'

const props = defineProps<{ library: ReturnType<typeof createLibraryState> }>()
const paper = computed(() => props.library.selected.value)
const removing = ref(false)
const confirm = useConfirm()

const note = ref('')
const savingNote = ref(false)
const noteSaved = ref(false)
const noteDirty = computed(() => (paper.value?.note ?? '') !== note.value)

watch(
  () => paper.value?.id,
  () => {
    note.value = paper.value?.note ?? ''
    noteSaved.value = false
  },
  { immediate: true },
)

async function changeStatus(value: string | null) {
  if (!paper.value || !value || value === paper.value.read_status) return
  await props.library.changeReading(paper.value, { read_status: value })
}

async function saveNote() {
  if (!paper.value) return
  savingNote.value = true
  try {
    noteSaved.value = await props.library.changeReading(paper.value, { note: note.value })
    if (noteSaved.value) {
      note.value = paper.value?.note ?? ''
      setTimeout(() => (noteSaved.value = false), 2000)
    }
  } finally {
    savingNote.value = false
  }
}

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

    <SelectButton
      :model-value="paper.read_status"
      :options="[...READ_STATUSES]"
      option-label="label"
      option-value="value"
      :allow-empty="false"
      size="small"
      aria-label="읽기 상태"
      @update:model-value="changeStatus"
    />

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
      <label for="note" class="text-sm text-surface-500">메모</label>
      <Textarea id="note" v-model="note" auto-resize rows="5" placeholder="읽으며 남길 내용을 적으세요." fluid />
      <div class="flex items-center gap-2">
        <Button label="메모 저장" icon="pi pi-save" size="small" :disabled="!noteDirty" :loading="savingNote" @click="saveNote" />
        <span v-if="noteSaved" class="text-sm text-primary"><i class="pi pi-check" /> 저장됨</span>
      </div>
      <Message v-if="library.state.readingError" severity="error">{{ library.state.readingError }}</Message>
    </div>

    <div class="flex flex-col gap-2 border-t border-surface-200 pt-4 dark:border-surface-700">
      <ConfirmPopup />
      <Button label="서재에서 삭제" icon="pi pi-trash" severity="danger" outlined :loading="removing" @click="askRemove" />
      <Message v-if="library.state.removeError" severity="error">{{ library.state.removeError }}</Message>
    </div>
  </div>
</template>
