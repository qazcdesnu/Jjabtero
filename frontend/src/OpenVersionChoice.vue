<!-- @doc: docs/design/Reader.md#6-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import type { OpenVersion } from './api'

defineProps<{ versions: OpenVersion[]; busy?: boolean }>()
const emit = defineEmits<{ pick: [version: OpenVersion]; decline: [] }>()

function meta(version: OpenVersion): string {
  return [version.authors.join(', '), version.year, version.venue].filter(Boolean).join(' · ')
}
</script>

<template>
  <div class="open-versions flex flex-col gap-2 rounded-md border border-amber-300 bg-amber-50 p-2 text-sm dark:border-amber-700 dark:bg-amber-950">
    <p>공개된 PDF가 없습니다. 비슷한 공개판이 있습니다. 이 PDF를 받을까요?</p>
    <div v-for="version in versions" :key="version.openalex_id" class="flex flex-col gap-1">
      <a :href="version.pdf_url" target="_blank" rel="noopener" class="leading-snug font-medium text-primary hover:underline">{{
        version.title
      }}</a>
      <span class="text-xs text-surface-500">{{ meta(version) }}</span>
      <Button label="이 PDF 받기" icon="pi pi-download" size="small" class="self-start" :loading="busy" @click="emit('pick', version)" />
    </div>
    <Button label="받지 않기" size="small" severity="secondary" text class="self-start" :disabled="busy" @click="emit('decline')" />
  </div>
</template>
