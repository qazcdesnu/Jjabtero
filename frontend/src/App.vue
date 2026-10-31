<!-- @doc: docs/design/AppSkeleton.md#3-프론트엔드-앱 -->
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchHealth, type Health } from './api'

const health = ref<Health | null>(null)
const failed = ref(false)

onMounted(async () => {
  try {
    health.value = await fetchHealth()
  } catch {
    failed.value = true
  }
})
</script>

<template>
  <main>
    <h1>Jjabtero</h1>
    <p v-if="health">서버 연결됨 (버전 {{ health.version }})</p>
    <p v-else-if="failed">서버에 연결할 수 없습니다.</p>
    <p v-else>서버 확인 중…</p>
  </main>
</template>
