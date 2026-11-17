<!-- @doc: docs/design/Reader.md#6-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Message from 'primevue/message'
import { ref, watch } from 'vue'
import { pdfUrl, type Paper } from './api'
import OpenVersionChoice from './OpenVersionChoice.vue'
import { createPdfState } from './pdfState'

const props = defineProps<{ paper: Paper }>()
const emit = defineEmits<{ changed: []; read: [paper: Paper] }>()
const pdf = createPdfState(() => emit('changed'))
const fileInput = ref<HTMLInputElement | null>(null)

watch(
  () => props.paper.id,
  () => pdf.reset(),
)

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) await pdf.upload(props.paper.id, file)
  input.value = ''
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <span class="text-sm text-surface-500">PDF</span>
    <div class="flex flex-wrap items-center gap-2">
      <template v-if="paper.has_pdf">
        <Button label="읽기" icon="pi pi-book" size="small" @click="emit('read', paper)" />
        <a :href="pdfUrl(paper.id)" target="_blank" rel="noopener" class="text-sm text-primary hover:underline">새 탭에서 열기</a>
      </template>
      <Button
        v-else
        label="PDF 받기"
        icon="pi pi-download"
        size="small"
        :loading="pdf.state.busy"
        @click="pdf.fetchOpen(paper.id)"
      />
      <Button
        :label="paper.has_pdf ? 'PDF 바꾸기' : 'PDF 올리기'"
        icon="pi pi-upload"
        size="small"
        severity="secondary"
        outlined
        :disabled="pdf.state.busy"
        @click="fileInput?.click()"
      />
      <input ref="fileInput" type="file" accept="application/pdf,.pdf" class="hidden" @change="onFile" />
    </div>
    <p v-if="paper.has_pdf && paper.pdf_source === 'alternate'" class="text-xs text-surface-500">
      비슷한 공개판에서 받은 PDF입니다. 판이 달라 쪽 번호나 내용이 다를 수 있습니다.
      <a v-if="paper.pdf_source_url" :href="paper.pdf_source_url" target="_blank" rel="noopener" class="text-primary hover:underline">출처</a>
    </p>
    <OpenVersionChoice
      v-if="pdf.state.alternatives.length"
      :versions="pdf.state.alternatives"
      :busy="pdf.state.busy"
      @pick="(version) => pdf.fetchAlternative(paper.id, version)"
      @decline="pdf.declineAlternatives()"
    />
    <p v-if="!paper.has_pdf" class="text-xs text-surface-500">
      "PDF 받기"는 arXiv와 오픈 액세스로 공개된 PDF를 찾아 받습니다. 없으면 가진 PDF를 올려 주세요.
    </p>
    <Message v-if="pdf.state.message" severity="success" size="small" variant="simple">{{ pdf.state.message }}</Message>
    <Message v-if="pdf.state.error" severity="error" size="small">{{ pdf.state.error }}</Message>
  </div>
</template>
