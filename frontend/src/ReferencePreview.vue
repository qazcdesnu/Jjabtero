<!-- @doc: docs/design/ReaderCitations.md#5-상자 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { computed } from 'vue'
import { readTarget, type createReferencePreview } from './referencePreview'

const props = defineProps<{ preview: ReturnType<typeof createReferencePreview> }>()
const state = computed(() => props.preview.state)
const work = computed(() => state.value.result?.work ?? null)
const target = computed(() => (state.value.result ? readTarget(state.value.result) : null))
const meta = computed(() => {
  const found = work.value
  if (!found) return ''
  const authors = found.authors.length > 3 ? `${found.authors.slice(0, 3).join(', ')} 외` : found.authors.join(', ')
  return [authors, found.year, found.venue].filter(Boolean).join(' · ')
})
const stored = computed(() => Boolean(work.value?.library_paper_id && state.value.result?.has_pdf))
</script>

<template>
  <div
    v-if="state.open"
    class="reader-popup reader-reference absolute z-30 flex w-96 max-w-[90vw] flex-col gap-2 rounded-md border border-surface-200 bg-surface-0 p-3 text-sm shadow-lg dark:border-surface-700 dark:bg-surface-800"
    :class="{ '-translate-y-full': state.place.above }"
    :style="{ left: `${state.place.left}px`, top: `${state.place.top}px` }"
    @mouseenter="preview.enterBox()"
    @mouseleave="preview.leaveBox()"
    @mousedown.stop
    @mouseup.stop
  >
    <template v-if="work">
      <a
        :href="work.doi ? `https://doi.org/${work.doi}` : `https://openalex.org/${work.openalex_id}`"
        target="_blank"
        rel="noopener"
        class="leading-snug font-medium hover:underline"
        >{{ work.title ?? work.openalex_id }}</a
      >
      <span class="text-xs text-surface-500">{{ meta }}</span>
      <div class="flex flex-wrap items-center gap-2 text-xs text-surface-500">
        <span v-if="work.cited_by_count !== null">피인용 {{ work.cited_by_count.toLocaleString() }}</span>
        <Tag v-if="work.library_paper_id" severity="success" value="서재에 있음" />
        <Tag v-if="stored" severity="info" value="PDF 있음" />
      </div>
      <div class="flex flex-wrap items-center gap-1">
        <Button
          v-if="!stored"
          label="서재에 담고 PDF 받기"
          icon="pi pi-download"
          size="small"
          :loading="state.working"
          @click="preview.addAndFetch()"
        />
        <a
          v-if="target"
          :href="target.url"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-1 rounded px-2 py-1 text-primary hover:bg-surface-100 dark:hover:bg-surface-700"
        >
          <i class="pi pi-external-link text-xs" />{{ target.label }}
        </a>
      </div>
      <p v-if="state.message" class="text-xs text-surface-600 dark:text-surface-300">{{ state.message }}</p>
    </template>
    <p v-else-if="state.loading" class="text-surface-500">찾는 중…</p>
    <p v-else-if="state.error" class="text-red-600 dark:text-red-400">{{ state.error }}</p>
    <p v-else class="text-surface-500">이 참고문헌을 찾지 못했습니다.</p>
    <p v-if="state.text" class="border-t border-surface-200 pt-2 text-xs leading-snug text-surface-500 dark:border-surface-700">
      {{ state.text }}
    </p>
  </div>
</template>
