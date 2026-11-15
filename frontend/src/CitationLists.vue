<!-- @doc: docs/design/Citations.md#6-api와-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'
import { computed, ref, watch } from 'vue'
import type { CitedWork } from './api'
import { createCitationListState } from './citationListState'

const props = defineProps<{ paperId: number }>()
const emit = defineEmits<{ added: [] }>()
const lists = createCitationListState(() => emit('added'))
const tab = ref<'citations' | 'references'>('citations')

watch(
  () => props.paperId,
  (paperId) => lists.load(paperId),
  { immediate: true },
)

const data = computed(() => lists.state.data)
const tabs = computed(() => [
  { value: 'citations', label: `피인용 ${data.value?.citations.length ?? 0}` },
  { value: 'references', label: `참고문헌 ${data.value?.references.length ?? 0}` },
])
const items = computed<CitedWork[]>(() => (data.value ? data.value[tab.value] : []))

function authorLine(work: CitedWork): string {
  if (work.authors.length === 0) return ''
  return work.authors.length > 3 ? `${work.authors.slice(0, 3).join(', ')} 외` : work.authors.join(', ')
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center justify-between">
      <span class="text-sm text-surface-500">인용</span>
      <Button icon="pi pi-refresh" text rounded size="small" aria-label="인용 목록 다시 읽기" @click="lists.load(paperId)" />
    </div>
    <p v-if="lists.state.loading && !data" class="text-xs text-surface-500">불러오는 중…</p>
    <Message v-if="lists.state.error" severity="error" size="small">{{ lists.state.error }}</Message>
    <template v-if="data">
      <p v-if="data.state === 'no_doi'" class="text-xs text-surface-500">DOI가 없어 OpenAlex와 연결할 수 없습니다.</p>
      <p v-else-if="data.state === 'not_found'" class="text-xs text-surface-500">OpenAlex에서 이 논문을 찾지 못했습니다.</p>
      <p v-else-if="data.state === 'pending'" class="text-xs text-surface-500">
        인용 데이터를 받는 중입니다. 잠시 뒤 다시 읽어 주세요.
      </p>
      <template v-else>
        <SelectButton v-model="tab" :options="tabs" option-label="label" option-value="value" :allow-empty="false" size="small" />
        <p v-if="tab === 'citations'" class="text-xs text-surface-500">
          공개 후 1년({{ data.window_start }} ~ {{ data.window_end }}) 안에 인용한 {{ data.citing_total }}편 가운데 피인용 많은 순
          {{ data.citations.length }}편입니다.
        </p>
        <p v-if="items.length === 0" class="text-xs text-surface-500">목록이 비어 있습니다.</p>
        <ul class="flex flex-col divide-y divide-surface-100 dark:divide-surface-800">
          <li v-for="work in items" :key="work.openalex_id" class="flex flex-col gap-1 py-2">
            <a
              :href="work.doi ? `https://doi.org/${work.doi}` : `https://openalex.org/${work.openalex_id}`"
              target="_blank"
              rel="noopener"
              class="text-sm leading-snug font-medium hover:underline"
            >
              {{ work.title ?? work.openalex_id }}
            </a>
            <span class="text-xs text-surface-500">
              {{ [authorLine(work), work.year, work.venue].filter(Boolean).join(' · ') }}
            </span>
            <div class="flex flex-wrap items-center gap-2 text-xs text-surface-500">
              <span v-if="work.cited_by_count !== null">피인용 {{ work.cited_by_count.toLocaleString() }}</span>
              <span v-if="work.shared_refs">공유 참고문헌 {{ work.shared_refs }}</span>
              <Tag v-if="work.library_paper_id" severity="success" value="서재에 있음" />
              <Button
                v-else
                label="서재에 담기"
                icon="pi pi-plus"
                size="small"
                text
                :loading="lists.state.adding.includes(work.openalex_id)"
                @click="lists.add(work)"
              />
            </div>
            <Message v-if="lists.state.addErrors[work.openalex_id]" severity="error" size="small">
              {{ lists.state.addErrors[work.openalex_id] }}
            </Message>
          </li>
        </ul>
      </template>
    </template>
  </div>
</template>
