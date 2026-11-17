<!-- @doc: docs/design/LibraryView.md#3-화면 -->
<!-- @doc: docs/design/LibraryFilter.md#4-화면 -->
<!-- @doc: docs/design/ReadingStatus.md#3-화면 -->
<!-- @doc: docs/design/Tags.md#4-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Chip from 'primevue/chip'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import Tag from 'primevue/tag'
import { computed, ref } from 'vue'
import type { Paper } from './api'
import { ITEM_TYPE_LABELS, READ_STATUSES, formatDate, formatDateTime, readStatusInfo, timeKey } from './labels'
import { isFilterActive } from './libraryFilter'
import { createLibraryState } from './libraryState'

const props = defineProps<{ library: ReturnType<typeof createLibraryState> }>()
const state = props.library.state

const itemTypeOptions = Object.entries(ITEM_TYPE_LABELS).map(([value, label]) => ({ value, label }))
const filtering = computed(() => isFilterActive(state.filter))

const bulkTag = ref('')
const allChecked = computed(
  () => props.library.visible.value.length > 0 && props.library.visible.value.every((paper) => state.checked.includes(paper.id)),
)

async function bulk(mode: 'add' | 'remove') {
  const name = bulkTag.value.trim()
  if (!name) return
  if (await props.library.tagChecked([name], mode)) bulkTag.value = ''
}

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
        <span class="text-sm text-surface-500">
          {{ filtering ? `전체 ${state.papers.length}편 중 ${library.visible.value.length}편` : `${state.papers.length}편` }}
        </span>
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

    <div class="flex flex-wrap items-center gap-2">
      <IconField class="min-w-56 flex-1">
        <InputIcon class="pi pi-filter" />
        <InputText v-model="state.filter.text" placeholder="제목, 저자, 태그 등으로 거르기" fluid size="small" />
      </IconField>
      <MultiSelect
        v-model="state.filter.itemTypes"
        :options="itemTypeOptions"
        option-label="label"
        option-value="value"
        placeholder="종류"
        :max-selected-labels="1"
        selected-items-label="종류 {0}개"
        size="small"
        class="w-36"
      />
      <MultiSelect
        v-model="state.filter.readStatuses"
        :options="[...READ_STATUSES]"
        option-label="label"
        option-value="value"
        placeholder="상태"
        :max-selected-labels="1"
        selected-items-label="상태 {0}개"
        size="small"
        class="w-32"
      />
      <InputNumber v-model="state.filter.yearFrom" placeholder="연도부터" :use-grouping="false" size="small" input-class="w-24" />
      <span class="text-surface-400">–</span>
      <InputNumber v-model="state.filter.yearTo" placeholder="연도까지" :use-grouping="false" size="small" input-class="w-24" />
      <Button v-if="filtering" label="필터 지우기" icon="pi pi-filter-slash" severity="secondary" text size="small" @click="library.clearFilter()" />
    </div>
    <div v-if="state.filter.tags.length > 0" class="flex flex-wrap items-center gap-2">
      <span class="text-xs text-surface-500">태그</span>
      <Chip v-for="tag in state.filter.tags" :key="tag" :label="tag" icon="pi pi-tag" removable @remove="library.toggleTag(tag)" />
    </div>

    <Message v-if="state.error" severity="warn">{{ state.error }}</Message>

    <div
      v-if="state.checked.length > 0"
      class="flex flex-wrap items-center gap-2 rounded-md border border-primary-200 bg-primary-50 px-3 py-2 text-sm dark:border-primary-800 dark:bg-primary-950"
    >
      <span class="font-medium">고른 {{ state.checked.length }}편</span>
      <InputText
        v-model="bulkTag"
        size="small"
        class="w-40"
        placeholder="태그 이름"
        list="bulk-tag-names"
        aria-label="고른 논문에 붙이거나 뗄 태그"
        @keydown.enter.prevent="bulk('add')"
      />
      <datalist id="bulk-tag-names">
        <option v-for="tag in library.tags.value" :key="tag.name" :value="tag.name" />
      </datalist>
      <Button label="태그 붙이기" icon="pi pi-tag" size="small" :disabled="!bulkTag.trim()" @click="bulk('add')" />
      <Button label="태그 떼기" size="small" severity="secondary" outlined :disabled="!bulkTag.trim()" @click="bulk('remove')" />
      <Button label="고르기 해제" size="small" severity="secondary" text @click="state.checked = []" />
      <Message v-if="state.tagError" severity="error" size="small" class="w-full">{{ state.tagError }}</Message>
    </div>

    <DataTable
      v-model:selection="selection"
      :value="library.visible.value"
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
          <template v-if="state.loading">불러오는 중입니다…</template>
          <template v-else-if="state.papers.length > 0">조건에 맞는 논문이 없습니다.</template>
          <template v-else>서재가 비었습니다. "논문 검색"에서 논문을 넣으세요.</template>
        </div>
      </template>
      <Column header-style="width: 2.5rem">
        <template #header>
          <Checkbox :model-value="allChecked" binary aria-label="보이는 논문 모두 고르기" @update:model-value="library.toggleAllVisible()" />
        </template>
        <template #body="{ data }">
          <span @click.stop>
            <Checkbox
              :model-value="state.checked.includes(data.id)"
              binary
              :aria-label="`${data.title} 고르기`"
              @update:model-value="library.toggleChecked(data.id)"
            />
          </span>
        </template>
      </Column>
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
      <Column field="read_status" header="상태" sortable header-style="width: 6.5rem">
        <template #body="{ data }">
          <Tag :value="readStatusInfo(data.read_status).label" :severity="readStatusInfo(data.read_status).severity" />
        </template>
      </Column>
      <Column field="item_type" header="종류" sortable header-style="width: 6.5rem">
        <template #body="{ data }">
          <span class="text-sm">{{ ITEM_TYPE_LABELS[data.item_type] ?? data.item_type }}</span>
        </template>
      </Column>
      <Column
        field="created_at"
        :sort-field="(paper: Paper) => timeKey(paper.created_at)"
        header="담은 날"
        sortable
        header-style="width: 7.5rem"
      >
        <template #body="{ data }">
          <span class="text-sm tabular-nums" :title="formatDateTime(data.created_at)">{{ formatDate(data.created_at) }}</span>
        </template>
      </Column>

    </DataTable>
  </div>
</template>
