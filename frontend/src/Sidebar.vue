<!-- @doc: docs/design/UiLayout.md#3-화면-배치 -->
<script setup lang="ts">
import { VIEWS } from './navigation'

const view = defineModel<string>({ required: true })
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
  </nav>
</template>
