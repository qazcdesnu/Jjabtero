<!-- @doc: docs/design/CitationStyles.md#5-복사 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { computed, ref } from 'vue'
import { CITATION_STYLES, copyCitation, type CitableWork } from './citationStyles'

const props = defineProps<{ work: CitableWork }>()
const visible = defineModel<boolean>('visible', { required: true })
const copied = ref('')
const failed = ref('')
let timer: ReturnType<typeof setTimeout> | null = null

const entries = computed(() => CITATION_STYLES.map((style) => ({ ...style, citation: style.format(props.work) })))

async function copy(id: string) {
  const entry = entries.value.find((item) => item.id === id)
  if (!entry) return
  failed.value = ''
  try {
    await copyCitation(entry.citation)
    copied.value = id
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => (copied.value = ''), 2000)
  } catch (error) {
    failed.value = `복사하지 못했습니다: ${error instanceof Error ? error.message : String(error)}`
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal header="인용" :style="{ width: '44rem' }" :breakpoints="{ '768px': '95vw' }" dismissable-mask>
    <p v-if="failed" class="mb-2 text-sm text-red-600 dark:text-red-400">{{ failed }}</p>
    <ul class="flex flex-col divide-y divide-surface-200 dark:divide-surface-700">
      <li v-for="entry in entries" :key="entry.id" class="flex items-start gap-3 py-2">
        <span class="w-20 shrink-0 pt-1 text-right text-sm font-medium text-surface-500">{{ entry.label }}</span>
        <pre
          v-if="entry.id === 'bibtex'"
          class="min-w-0 flex-1 overflow-x-auto rounded bg-surface-100 p-2 font-mono text-xs leading-snug dark:bg-surface-800"
          >{{ entry.citation.text }}</pre
        >
        <!-- html은 escapeHtml로 만든 조각과 <i>만 들어 있다. -->
        <p v-else class="min-w-0 flex-1 text-sm leading-snug select-text" v-html="entry.citation.html" />
        <Button
          :icon="copied === entry.id ? 'pi pi-check' : 'pi pi-copy'"
          :label="copied === entry.id ? '복사됨' : '복사'"
          size="small"
          text
          :severity="copied === entry.id ? 'success' : undefined"
          :aria-label="`${entry.label} 양식 복사`"
          @click="copy(entry.id)"
        />
      </li>
    </ul>
  </Dialog>
</template>
