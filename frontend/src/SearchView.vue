<!-- @doc: docs/design/PaperSearch.md#4-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { computed } from 'vue'
import type { SearchResult } from './api'
import { SEARCH_SOURCES, createSearchState, sourceLabel } from './searchState'

const props = defineProps<{ search: ReturnType<typeof createSearchState> }>()
const state = props.search.state

const selection = computed({
  get: () => props.search.rows.value.find((row) => row.key === state.selectedKey) ?? null,
  set: (row: SearchResult | null) => props.search.select(row),
})
</script>

<template>
  <div class="flex h-full flex-col gap-3 p-4">
    <form class="flex flex-wrap items-center gap-3" @submit.prevent="search.run()">
      <IconField class="min-w-64 flex-1">
        <InputIcon class="pi pi-search" />
        <InputText v-model="state.query" placeholder="논문 제목, 저자, 주제로 검색" fluid />
      </IconField>
      <div class="flex items-center gap-3">
        <label v-for="source in SEARCH_SOURCES" :key="source.name" class="flex items-center gap-1 text-sm">
          <Checkbox v-model="state.sources" :value="source.name" />
          {{ source.label }}
        </label>
      </div>
      <Button type="submit" label="검색" icon="pi pi-search" :loading="state.searching" :disabled="!search.canRun.value" />
    </form>

    <Message v-if="state.error" severity="error">{{ state.error }}</Message>
    <Message v-for="failure in state.failures" :key="failure.source" severity="warn">
      {{ failure.source }} 검색 실패: {{ failure.message }}
    </Message>

    <DataTable
      v-model:selection="selection"
      :value="search.rows.value"
      data-key="key"
      selection-mode="single"
      :meta-key-selection="false"
      scrollable
      scroll-height="flex"
      size="small"
      striped-rows
      table-class="table-fixed"
      class="min-h-0 flex-1"
    >
      <template #empty>
        <div class="py-8 text-center text-surface-500">
          {{ state.searching ? '검색 중입니다…' : '검색어를 넣고 검색하세요.' }}
        </div>
      </template>
      <Column header="제목">
        <template #body="{ data }">
          <span class="line-clamp-2 font-medium" :title="data.title">{{ data.title }}</span>
        </template>
      </Column>
      <Column header="저자" header-style="width: 11rem">
        <template #body="{ data }">
          <span class="block truncate text-sm" :title="data.authors.join(', ')">
            {{ data.authors.slice(0, 3).join(', ') }}{{ data.authors.length > 3 ? ' 외' : '' }}
          </span>
        </template>
      </Column>
      <Column field="year" header="연도" header-style="width: 4.5rem" body-class="text-sm" />
      <Column header="게재처" header-style="width: 10rem">
        <template #body="{ data }">
          <span class="block truncate text-sm" :title="data.venue ?? ''">{{ data.venue }}</span>
        </template>
      </Column>
      <Column header="출처" header-style="width: 6.5rem">
        <template #body="{ data }"><Tag :value="sourceLabel(data.source)" severity="secondary" /></template>
      </Column>
      <Column header="" header-style="width: 3rem">
        <template #body="{ data }">
          <i v-if="search.isInLibrary(data)" v-tooltip="'서재에 있음'" class="pi pi-check-circle text-primary" aria-label="서재에 있음" />
        </template>
      </Column>
    </DataTable>
  </div>
</template>
