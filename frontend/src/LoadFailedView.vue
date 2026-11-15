<!-- @doc: docs/design/UiLayout.md#5-나중에-불러오는-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'

defineProps<{ error?: unknown }>()

function reload() {
  window.location.reload()
}
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center gap-3 p-6 text-center text-surface-500">
    <i class="pi pi-exclamation-triangle text-3xl" />
    <p>화면을 불러오지 못했습니다. 앱이 새로 배포되었거나 연결이 끊겼을 수 있습니다.</p>
    <p v-if="error" class="text-xs">{{ error instanceof Error ? error.message : String(error) }}</p>
    <Button label="새로고침" icon="pi pi-refresh" size="small" @click="reload" />
  </div>
</template>
