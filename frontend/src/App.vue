<!-- @doc: docs/design/AppSkeleton.md#3-프론트엔드-앱 -->
<!-- @doc: docs/design/UiLayout.md#3-화면-배치 -->
<!-- @doc: docs/design/LibraryView.md#3-화면 -->
<!-- @doc: docs/design/LibraryFilter.md#3-화면-상태 -->
<script setup lang="ts">
import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'
import Tag from 'primevue/tag'
import { onMounted, ref, watch } from 'vue'
import { fetchHealth, type Health } from './api'
import LibraryView from './LibraryView.vue'
import { createLibraryState } from './libraryState'
import { DEFAULT_VIEW } from './navigation'
import PaperDetail from './PaperDetail.vue'
import { createSearchState } from './searchState'
import SearchResultDetail from './SearchResultDetail.vue'
import SearchView from './SearchView.vue'
import Sidebar from './Sidebar.vue'

const view = ref<string>(DEFAULT_VIEW)
const search = createSearchState()
const library = createLibraryState()

watch(view, (name) => {
  if (name === 'library') library.load()
})
const health = ref<Health | null>(null)
const healthFailed = ref(false)

onMounted(async () => {
  library.load()
  try {
    health.value = await fetchHealth()
  } catch {
    healthFailed.value = true
  }
})
</script>

<template>
  <div class="flex h-full flex-col bg-surface-50 text-surface-800 dark:bg-surface-950 dark:text-surface-100">
    <header
      class="flex items-center justify-between border-b border-surface-200 bg-surface-0 px-4 py-2 dark:border-surface-700 dark:bg-surface-900"
    >
      <div class="flex items-center gap-2">
        <i class="pi pi-bookmark-fill text-primary text-lg" />
        <span class="text-lg font-semibold tracking-tight">Jjabtero</span>
      </div>
      <Tag v-if="health" severity="success" :value="`서버 연결됨 · v${health.version}`" />
      <Tag v-else-if="healthFailed" severity="danger" value="서버에 연결할 수 없음" />
      <Tag v-else severity="secondary" value="서버 확인 중" />
    </header>

    <Splitter class="min-h-0 flex-1 rounded-none border-0">
      <SplitterPanel :size="15" :min-size="10" class="overflow-auto">
        <Sidebar v-model="view" :library="library" />
      </SplitterPanel>
      <SplitterPanel :size="55" :min-size="30" class="overflow-auto">
        <SearchView v-if="view === 'search'" :search="search" />
        <LibraryView v-else :library="library" />
      </SplitterPanel>
      <SplitterPanel :size="30" :min-size="20" class="overflow-auto">
        <SearchResultDetail v-if="view === 'search' && search.selected.value" :search="search" />
        <PaperDetail v-else-if="view === 'library' && library.selected.value" :library="library" />
        <div v-else class="flex h-full flex-col items-center justify-center gap-2 text-surface-500">
          <i class="pi pi-file text-4xl" />
          <p>항목을 고르면 여기에 상세가 보입니다.</p>
        </div>
      </SplitterPanel>
    </Splitter>
  </div>
</template>
