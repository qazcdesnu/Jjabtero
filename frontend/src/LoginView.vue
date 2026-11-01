<!-- @doc: docs/design/Auth.md#6-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import { loginUrl } from './auth'

function signIn() {
  window.location.href = loginUrl(window.location.pathname + window.location.search)
}
</script>

<template>
  <div class="flex h-full items-center justify-center bg-surface-50 dark:bg-surface-950">
    <div class="flex w-80 flex-col items-center gap-4 rounded-xl border border-surface-200 bg-surface-0 p-8 dark:border-surface-700 dark:bg-surface-900">
      <i class="pi pi-bookmark-fill text-primary text-3xl" />
      <h1 class="text-xl font-semibold">Jjabtero</h1>
      <p class="text-center text-sm break-keep text-surface-500">허용된 구글 계정으로 로그인해야 쓸 수 있습니다.</p>
      <Button label="Google로 로그인" icon="pi pi-google" class="w-full" @click="signIn" />
    </div>
  </div>
</template>
