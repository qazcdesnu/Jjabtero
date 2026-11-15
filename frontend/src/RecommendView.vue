<!-- @doc: docs/design/Citations.md#6-api와-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { onMounted } from 'vue'
import type { RecommendedWork } from './api'
import { createRecommendState } from './recommendState'

const emit = defineEmits<{ added: [] }>()
const recommend = createRecommendState(() => emit('added'))
onMounted(() => recommend.load())

function meta(work: RecommendedWork): string {
  const authors = work.authors.length > 3 ? `${work.authors.slice(0, 3).join(', ')} 외` : work.authors.join(', ')
  return [authors, work.year, work.venue].filter(Boolean).join(' · ')
}
</script>

<template>
  <section class="mx-auto flex max-w-3xl flex-col gap-4 p-6">
    <header class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-xl font-semibold">추천</h2>
        <p class="text-sm text-surface-500">
          서재 논문들과 인용으로 가까운 논문 가운데 아직 서재에 없는 것입니다. 여러 서재 논문과 이어질수록 위에 옵니다. 담기 전에는
          서재에 들어가지 않습니다.
        </p>
      </div>
      <Button icon="pi pi-refresh" label="다시 계산" size="small" severity="secondary" :loading="recommend.state.loading" @click="recommend.load()" />
    </header>
    <Message v-if="recommend.state.error" severity="error">{{ recommend.state.error }}</Message>
    <p v-if="recommend.state.loading && !recommend.state.data" class="text-sm text-surface-500">계산하는 중…</p>
    <template v-if="recommend.state.data">
      <p class="text-xs text-surface-500">
        서재 논문 {{ recommend.state.data.papers }}편 가운데 인용 데이터가 있는 {{ recommend.state.data.papers_used }}편으로 계산했습니다.
      </p>
      <p v-if="recommend.state.data.works.length === 0" class="text-sm text-surface-500">
        아직 추천할 논문이 없습니다. 서재에 논문을 담으면 인용 데이터를 받은 뒤 추천이 생깁니다.
      </p>
      <ol class="flex flex-col divide-y divide-surface-200 dark:divide-surface-700">
        <li v-for="(work, index) in recommend.state.data.works" :key="work.openalex_id" class="flex gap-3 py-3">
          <span class="w-6 shrink-0 text-right text-sm text-surface-400 tabular-nums">{{ index + 1 }}</span>
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <a
              :href="work.doi ? `https://doi.org/${work.doi}` : `https://openalex.org/${work.openalex_id}`"
              target="_blank"
              rel="noopener"
              class="leading-snug font-medium hover:underline"
            >
              {{ work.title ?? work.openalex_id }}
            </a>
            <span class="text-xs text-surface-500">{{ meta(work) }}</span>
            <span class="text-xs text-surface-500">
              이어진 서재 논문: {{ work.sources.map((source) => source.title).join(', ') }}
            </span>
            <div class="flex flex-wrap items-center gap-2 text-xs text-surface-500">
              <span>점수 {{ work.score.toFixed(2) }}</span>
              <span v-if="work.cited_by_count !== null">피인용 {{ work.cited_by_count.toLocaleString() }}</span>
              <Tag v-if="recommend.state.added.includes(work.openalex_id)" severity="success" value="서재에 담음" />
              <Button
                v-else
                label="서재에 담기"
                icon="pi pi-plus"
                size="small"
                text
                :loading="recommend.state.adding.includes(work.openalex_id)"
                @click="recommend.add(work)"
              />
            </div>
            <Message v-if="recommend.state.addErrors[work.openalex_id]" severity="error" size="small">
              {{ recommend.state.addErrors[work.openalex_id] }}
            </Message>
          </div>
        </li>
      </ol>
    </template>
  </section>
</template>
