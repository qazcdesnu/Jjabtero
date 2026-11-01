<!-- @doc: docs/design/LibraryView.md#3-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Message from 'primevue/message'
import { computed } from 'vue'
import type { Paper } from './api'
import { ITEM_TYPE_LABELS, formatDate } from './labels'
import { createLibraryState } from './libraryState'

const props = defineProps<{ library: ReturnType<typeof createLibraryState> }>()
const state = props.library.state

const selection = computed({
  get: () => props.library.selected.value,
  set: (paper: Paper | null) => props.library.select(paper),
})
</script>

<template>
  <div class="flex h-full flex-col gap-3 p-4">
    <div class="flex items-center justify-between">
      <div class="flex items-baseline gap-2">
        <h2 class="text-lg font-semibold">서재</h2>
        <span class="text-sm text-surface-500">{{ state.papers.length }}편</span>
      </div>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        aria-label="새로 고침"
        :loading="state.loading"
        @click="library.load()"
      />
    </div>

    <Message v-if="state.error" severity="warn">{{ state.error }}</Message>

    <DataTable
      v-model:selection="selection"
      :value="state.papers"
      data-key="id"
      selection-mode="single"
      :meta-key-selection="false"
      sort-mode="single"
      removable-sort
      scrollable
      scroll-height="flex"
      size="small"
      striped-rows
      table-class="table-fixed"
      class="min-h-0 flex-1"
    >
      <template #empty>
        <div class="py-8 text-center text-surface-500">
          {{ state.loading ? '불러오는 중입니다…' : '서재가 비었습니다. "논문 검색"에서 논문을 넣으세요.' }}
        </div>
      </template>
      <Column field="title" header="제목" sortable>
        <template #body="{ data }">
          <span class="line-clamp-2 font-medium" :title="data.title">{{ data.title }}</span>
        </template>
      </Column>
      <Column field="authors" header="저자" sortable header-style="width: 10rem">
        <template #body="{ data }">
          <span class="block truncate text-sm" :title="data.authors.join(', ')">
            {{ data.authors.slice(0, 3).join(', ') }}{{ data.authors.length > 3 ? ' 외' : '' }}
          </span>
        </template>
      </Column>
      <Column field="year" header="연도" sortable header-style="width: 5.25rem" body-class="text-sm" />
      <Column field="item_type" header="종류" sortable header-style="width: 6.5rem">
        <template #body="{ data }">
          <span class="text-sm">{{ ITEM_TYPE_LABELS[data.item_type] ?? data.item_type }}</span>
        </template>
      </Column>
      <Column field="created_at" header="추가일" sortable header-style="width: 7rem">
        <template #body="{ data }">
          <span class="text-sm tabular-nums">{{ formatDate(data.created_at) }}</span>
        </template>
      </Column>
    </DataTable>
  </div>
</template>
