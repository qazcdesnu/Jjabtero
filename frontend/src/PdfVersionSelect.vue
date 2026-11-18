<!-- @doc: docs/design/PdfVersions.md#6-화면 -->
<script setup lang="ts">
import Message from 'primevue/message'
import Select from 'primevue/select'
import { onMounted, watch } from 'vue'
import { createPdfVersionState } from './pdfVersionState'

const props = defineProps<{ paperId: number }>()
const emit = defineEmits<{ changed: [sha256: string] }>()
const versions = createPdfVersionState(
  () => props.paperId,
  (sha256) => emit('changed', sha256),
)

onMounted(() => versions.load())
watch(
  () => props.paperId,
  () => versions.load(),
)

function onChange(value: string | null) {
  if (value) void versions.choose(value)
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-1">
    <Select
      :model-value="versions.selected.value"
      :options="versions.groups.value"
      option-group-label="label"
      option-group-children="items"
      option-label="label"
      option-value="value"
      :placeholder="versions.state.saved.length ? '판 고르기' : '받을 판 고르기'"
      :loading="versions.state.searching || versions.state.busy"
      :disabled="versions.state.busy"
      :empty-message="versions.state.searching ? '판을 찾는 중입니다…' : '고를 수 있는 판이 없습니다.'"
      size="small"
      class="pdf-version-select w-full max-w-sm"
      aria-label="PDF 판"
      @show="versions.search()"
      @update:model-value="onChange"
    >
      <template #optiongroup="{ option }">
        <span class="text-xs font-semibold text-surface-500">{{ option.label }}</span>
      </template>
      <template #option="{ option }">
        <div class="flex min-w-0 flex-col">
          <span class="truncate">{{ option.label }}</span>
          <span v-if="option.detail" class="text-xs text-surface-500">{{ option.detail }}</span>
        </div>
      </template>
    </Select>
    <Message v-if="versions.state.searchError" severity="warn" size="small" variant="simple">
      받을 수 있는 판을 찾지 못했습니다. 받은 판은 고를 수 있습니다.
    </Message>
    <Message v-if="versions.state.error" severity="error" size="small" variant="simple">{{ versions.state.error }}</Message>
  </div>
</template>
