<!-- @doc: docs/design/PaperSearch.md#4-화면 -->
<script setup lang="ts">
import AutoComplete from 'primevue/autocomplete'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { computed, ref, watch } from 'vue'
import { ITEM_TYPE_LABELS, createSearchState, resultKey, sourceLabel } from './searchState'

const props = defineProps<{ search: ReturnType<typeof createSearchState> }>()
const result = computed(() => props.search.selected.value)
const tags = ref<string[]>([])
const adding = ref(false)

watch(
  () => props.search.state.selectedKey,
  () => {
    tags.value = []
  },
)

const addError = computed(() =>
  result.value ? props.search.state.addErrors[resultKey(result.value)] : undefined,
)

async function add() {
  if (!result.value) return
  adding.value = true
  try {
    await props.search.add(result.value, tags.value)
  } finally {
    adding.value = false
  }
}
</script>

<template>
  <div v-if="result" class="flex flex-col gap-4 p-4">
    <div class="flex flex-col gap-1">
      <div class="flex items-center gap-2 text-xs text-surface-500">
        <Tag :value="ITEM_TYPE_LABELS[result.item_type] ?? result.item_type" severity="secondary" />
        <span>{{ sourceLabel(result.source) }}</span>
      </div>
      <h2 class="text-lg leading-snug font-semibold">{{ result.title }}</h2>
      <p class="text-sm text-surface-600 dark:text-surface-300">
        {{ result.authors.join(', ') || '저자 정보 없음' }}
      </p>
    </div>

    <dl class="grid grid-cols-[5rem_1fr] gap-x-3 gap-y-2 text-sm">
      <dt class="text-surface-500">연도</dt>
      <dd>{{ result.year ?? '—' }}</dd>
      <dt class="text-surface-500">게재처</dt>
      <dd>{{ result.venue ?? '—' }}</dd>
      <dt class="text-surface-500">DOI</dt>
      <dd class="break-all">
        <a v-if="result.doi" :href="`https://doi.org/${result.doi}`" target="_blank" rel="noopener" class="text-primary hover:underline">{{ result.doi }}</a>
        <span v-else>—</span>
      </dd>
      <dt class="text-surface-500">원문</dt>
      <dd class="break-all">
        <a v-if="result.url" :href="result.url" target="_blank" rel="noopener" class="text-primary hover:underline">{{ result.url }}</a>
        <span v-else>—</span>
      </dd>
    </dl>

    <div v-if="search.isInLibrary(result)">
      <Tag value="서재에 있음" severity="success" icon="pi pi-check" />
    </div>
    <div v-else class="flex flex-col gap-2">
      <label class="text-sm text-surface-500" for="tags">태그 (선택, Enter로 추가)</label>
      <AutoComplete v-model="tags" input-id="tags" multiple :typeahead="false" fluid />
      <Button label="서재에 추가" icon="pi pi-plus" :loading="adding" @click="add" />
      <Message v-if="addError" severity="error">{{ addError }}</Message>
    </div>
  </div>
</template>
