<!-- @doc: docs/design/CitationStyles.md#5-복사 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import SelectButton from 'primevue/selectbutton'
import { computed, ref, watch } from 'vue'
import { CITATION_STYLES, copyCitation, type CitableWork, type CopyMode } from './citationStyles'

const props = defineProps<{ work: CitableWork }>()
const visible = defineModel<boolean>('visible', { required: true })
const copied = ref('')
const failed = ref('')
let timer: ReturnType<typeof setTimeout> | null = null

// 고른 복사 모드는 이 브라우저에 기억한다. 저장소를 못 쓰면 문서용으로 시작한다.
const MODE_KEY = 'jjabtero:cite-mode'
const modes = [
  { value: 'document', label: '문서용(워드·구글 문서)' },
  { value: 'latex', label: 'LaTeX' },
]
function savedMode(): CopyMode {
  try {
    return localStorage.getItem(MODE_KEY) === 'latex' ? 'latex' : 'document'
  } catch {
    return 'document'
  }
}
const mode = ref<CopyMode>(savedMode())
watch(mode, (value) => {
  copied.value = ''
  try {
    localStorage.setItem(MODE_KEY, value)
  } catch {
    // 기억하지 못해도 복사에는 지장이 없다.
  }
})

const entries = computed(() => CITATION_STYLES.map((style) => ({ ...style, citation: style.format(props.work) })))

async function copy(id: string) {
  const entry = entries.value.find((item) => item.id === id)
  if (!entry) return
  failed.value = ''
  try {
    await copyCitation(entry.citation, mode.value)
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
    <div class="mb-2 flex flex-wrap items-center gap-3">
      <SelectButton v-model="mode" :options="modes" option-label="label" option-value="value" :allow-empty="false" size="small" />
      <span class="text-xs text-surface-500">
        {{ mode === 'latex' ? '기울임은 \\textit, 주소는 \\url(url 패키지)로 씁니다.' : '붙여 넣으면 기울임이 그대로 남습니다.' }}
      </span>
    </div>
    <p v-if="failed" class="mb-2 text-sm text-red-600 dark:text-red-400">{{ failed }}</p>
    <ul class="flex flex-col divide-y divide-surface-200 dark:divide-surface-700">
      <li v-for="entry in entries" :key="entry.id" class="flex items-start gap-3 py-2">
        <span class="w-20 shrink-0 pt-1 text-right text-sm font-medium text-surface-500">{{ entry.label }}</span>
        <pre
          v-if="entry.id === 'bibtex' || mode === 'latex'"
          :class="{ 'break-words whitespace-pre-wrap': entry.id !== 'bibtex' }"
          class="min-w-0 flex-1 overflow-x-auto rounded bg-surface-100 p-2 font-mono text-xs leading-snug dark:bg-surface-800"
          >{{ mode === 'latex' ? entry.citation.latex : entry.citation.text }}</pre
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
