<!-- @doc: docs/design/Citations.md#6-api와-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Message from 'primevue/message'
import { onMounted, onUnmounted, ref } from 'vue'
import { fetchCitationStatus, refreshCitations, type CitationStatus } from './api'

const status = ref<CitationStatus | null>(null)
const failure = ref('')
const refreshing = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

async function load() {
  try {
    status.value = await fetchCitationStatus()
    failure.value = ''
  } catch (error) {
    failure.value = error instanceof Error ? error.message : String(error)
  }
}

async function refresh() {
  refreshing.value = true
  try {
    status.value = await refreshCitations()
    failure.value = ''
  } catch (error) {
    failure.value = error instanceof Error ? error.message : String(error)
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  load()
  timer = setInterval(load, 5000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="flex flex-col gap-3 rounded-lg border border-surface-200 p-4 dark:border-surface-700">
    <div class="flex items-center justify-between gap-3">
      <span class="font-medium">인용 데이터</span>
      <Button
        label="인용 데이터 새로 받기"
        icon="pi pi-refresh"
        size="small"
        severity="secondary"
        :loading="refreshing"
        @click="refresh"
      />
    </div>
    <p class="text-sm text-surface-500">
      서재 논문을 OpenAlex와 연결하고 참고문헌과 피인용을 받아 둡니다. 논문을 담으면 곧 받고, 7일마다 다시 받습니다. 받은 논문은 서재에 추가되지 않습니다.
    </p>
    <dl v-if="status" class="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
      <div><dt class="text-surface-500">서재 논문</dt><dd class="tabular-nums">{{ status.papers }}</dd></div>
      <div><dt class="text-surface-500">OpenAlex 연결</dt><dd class="tabular-nums">{{ status.linked }}</dd></div>
      <div><dt class="text-surface-500">찾지 못함</dt><dd class="tabular-nums">{{ status.not_found }}</dd></div>
      <div><dt class="text-surface-500">받은 논문</dt><dd class="tabular-nums">{{ status.fetched }}</dd></div>
    </dl>
    <p v-if="status" class="text-xs text-surface-500">
      {{ status.running ? '받는 중…' : status.last_run ? `마지막 갱신 ${new Date(status.last_run).toLocaleString()}` : '아직 갱신하지 않음' }}
    </p>
    <Message v-if="status?.error" severity="warn" size="small">{{ status.error }}</Message>
    <Message v-if="failure" severity="error" size="small">{{ failure }}</Message>
  </div>
</template>
