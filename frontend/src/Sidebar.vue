<!-- @doc: docs/design/UiLayout.md#3-화면-배치 -->
<!-- @doc: docs/design/LibraryFilter.md#4-화면 -->
<script setup lang="ts">
import { createLibraryState } from './libraryState'
import { VIEWS } from './navigation'

const props = defineProps<{ library: ReturnType<typeof createLibraryState> }>()
const view = defineModel<string>({ required: true })

function pickTag(name: string) {
  props.library.toggleTag(name)
  view.value = 'library'
}
</script>

<template>
  <nav class="flex flex-col gap-1 p-2">
    <button
      v-for="item in VIEWS"
      :key="item.name"
      type="button"
      class="flex items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors"
      :class="
        view === item.name
          ? 'bg-primary text-primary-contrast'
          : 'hover:bg-surface-100 dark:hover:bg-surface-800'
      "
      @click="view = item.name"
    >
      <i :class="item.icon" />
      {{ item.label }}
    </button>

    <h3 class="mt-4 px-3 text-xs font-semibold tracking-wide text-surface-500 uppercase">태그</h3>
    <p v-if="library.tags.value.length === 0" class="px-3 text-xs text-surface-400">
      논문에 태그를 붙이면 여기에 보입니다.
    </p>
    <button
      v-for="tag in library.tags.value"
      :key="tag.name"
      type="button"
      class="flex items-center justify-between gap-2 rounded-md px-3 py-1.5 text-left text-sm transition-colors"
      :class="
        library.state.filter.tags.includes(tag.name)
          ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-200'
          : 'hover:bg-surface-100 dark:hover:bg-surface-800'
      "
      @click="pickTag(tag.name)"
    >
      <span class="flex min-w-0 items-center gap-2">
        <i class="pi pi-tag text-xs" />
        <span class="truncate">{{ tag.name }}</span>
      </span>
      <span class="text-xs text-surface-500 tabular-nums">{{ tag.count }}</span>
    </button>
  </nav>
</template>
