<!-- @doc: docs/design/CitationGraph.md#4-화면 -->
<!-- @doc: docs/design/Tags.md#5-태그별-그래프 -->
<script setup lang="ts">
import { GraphChart } from 'echarts/charts'
import { DataZoomComponent, GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { init, use, type ECharts } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import SelectButton from 'primevue/selectbutton'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import { graphOption, yearLayout, type GraphLayout, type GraphPalette } from './graphOption'
import { createGraphState } from './graphState'

use([GraphChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

const props = withDefaults(
  defineProps<{ tags?: string[]; allTags?: { name: string; count: number }[] }>(),
  { tags: () => [], allTags: () => [] },
)
const emit = defineEmits<{ open: [paperId: number]; added: []; untag: [name: string]; 'update:tags': [names: string[]] }>()
// 왼쪽 목록의 태그 선택과 같은 상태다. 여기서 고르면 왼쪽에도 반영된다.
const tagOptions = computed(() => props.allTags.map((tag) => ({ value: tag.name, label: `${tag.name} (${tag.count})` })))
const graph = createGraphState(() => emit('added'), undefined, () => props.tags)
const layout = ref<GraphLayout>('year')
const layouts = [
  { value: 'year', label: '연도 순' },
  { value: 'force', label: '자유 배치' },
]
const container = ref<HTMLDivElement | null>(null)
const chart = shallowRef<ECharts | null>(null)
let resizer: ResizeObserver | null = null
const dark = window.matchMedia('(prefers-color-scheme: dark)')

const counts = computed(() => {
  const data = graph.state.data
  if (!data) return null
  const library = data.nodes.filter((node) => node.paper_id !== null)
  return {
    library: library.length,
    withData: library.filter((node) => node.has_data).length,
    outside: data.nodes.length - library.length,
    cites: data.edges.filter((edge) => edge.kind === 'cites').length,
    related: data.edges.filter((edge) => edge.kind === 'related').length,
    noYear: layout.value === 'year' ? yearLayout(data.nodes).hidden : 0,
    undated: layout.value === 'year' ? yearLayout(data.nodes, data.edges).undated : 0,
  }
})

function palette(): GraphPalette {
  return dark.matches
    ? { library: '#34d399', outside: '#94a3b8', text: '#e2e8f0', edge: '#64748b' }
    : { library: '#10b981', outside: '#94a3b8', text: '#334155', edge: '#94a3b8' }
}

function draw(): void {
  if (!chart.value || !graph.state.data) return
  chart.value.setOption(graphOption(graph.state.data, layout.value, palette()), true)
}

function meta(): string {
  const node = graph.selected.value
  if (!node) return ''
  const authors = node.authors.length > 3 ? `${node.authors.slice(0, 3).join(', ')} 외` : node.authors.join(', ')
  return [authors, node.year, node.venue].filter(Boolean).join(' · ')
}

watch(() => [graph.state.data, layout.value], draw)
watch(
  () => [graph.state.outside, props.tags.join('\u0000')],
  () => graph.load(),
)

onMounted(() => {
  if (container.value) {
    chart.value = init(container.value)
    chart.value.on('click', (params) => {
      if (params.dataType === 'node') graph.select((params.data as { id: string }).id)
    })
    resizer = new ResizeObserver(() => chart.value?.resize())
    resizer.observe(container.value)
    dark.addEventListener('change', draw)
  }
  graph.load()
})

onUnmounted(() => {
  resizer?.disconnect()
  dark.removeEventListener('change', draw)
  chart.value?.dispose()
})
</script>

<template>
  <section class="flex h-full flex-col gap-3 p-6">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 class="text-xl font-semibold">인용 그래프</h2>
        <p class="text-sm text-surface-500">
          서재 논문들이 인용으로 어떻게 이어지는지 봅니다. 화살표는 인용한 논문에서 인용된 논문으로 가고, 점선은 참고문헌을 많이
          공유하거나 함께 인용되는 사이입니다.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <SelectButton v-model="layout" :options="layouts" option-label="label" option-value="value" :allow-empty="false" size="small" />
        <MultiSelect
          :model-value="tags"
          :options="tagOptions"
          option-label="label"
          option-value="value"
          :placeholder="allTags.length ? '태그: 서재 전체' : '태그 없음'"
          :disabled="!allTags.length"
          :max-selected-labels="2"
          selected-items-label="태그 {0}개"
          filter
          filter-placeholder="태그 찾기"
          show-clear
          size="small"
          class="w-52"
          aria-label="그래프에 그릴 태그"
          @update:model-value="(names: string[] | null) => emit('update:tags', names ?? [])"
        />
        <label class="flex items-center gap-2 text-sm">
          <ToggleSwitch v-model="graph.state.outside" />
          추천 논문 함께 보기
        </label>
        <Button icon="pi pi-refresh" label="다시 그리기" size="small" severity="secondary" :loading="graph.state.loading" @click="graph.load()" />
      </div>
    </header>
    <div v-if="tags.length" class="flex flex-wrap items-center gap-2">
      <span class="text-xs text-surface-500">태그</span>
      <Chip v-for="tag in tags" :key="tag" :label="tag" icon="pi pi-tag" removable @remove="emit('untag', tag)" />
      <span class="text-xs text-surface-500">를 모두 가진 서재 논문만 그립니다.</span>
      <Button label="서재 전체 보기" size="small" text @click="emit('update:tags', [])" />
    </div>
    <Message v-if="graph.state.error" severity="error">{{ graph.state.error }}</Message>
    <p v-if="counts" class="text-xs text-surface-500">
      서재 논문 {{ counts.library }}편(인용 데이터 있음 {{ counts.withData }}편)<template v-if="counts.outside">, 추천 논문 {{ counts.outside }}편</template>,
      인용 선 {{ counts.cites }}개, 가까움 선 {{ counts.related }}개.
      <template v-if="counts.noYear">연도를 모르는 {{ counts.noYear }}편은 자유 배치에서만 보입니다.</template>
      <template v-if="layout === 'year'"
        >&nbsp;왼쪽이 선행, 오른쪽이 후행입니다. 같은 연도 안에서는 위가 먼저 공개된 논문이고, 서로 인용하면 인용된 논문이
        위입니다.<template v-if="counts.undated">
          같은 연도에 다른 논문이 있는데 공개일을 연도까지만 아는 {{ counts.undated }}편은 인용 관계로만 자리를 정하고, 인용 관계도
          없으면 그해 아래쪽에 둡니다(점에 마우스를 올리면 날짜와 정밀도가 보입니다).</template
        >
        휠로 연도 범위를 넓히고 좁힙니다.</template
      >
    </p>
    <div
      ref="container"
      class="min-h-[420px] flex-1 rounded border border-surface-200 bg-surface-0 dark:border-surface-700 dark:bg-surface-900"
    />
    <div
      v-if="graph.selected.value"
      class="flex items-start justify-between gap-4 rounded border border-surface-200 bg-surface-0 p-3 dark:border-surface-700 dark:bg-surface-900"
    >
      <div class="flex min-w-0 flex-col gap-1">
        <a
          v-if="graph.selected.value.doi || graph.selected.value.openalex_id"
          :href="
            graph.selected.value.doi
              ? `https://doi.org/${graph.selected.value.doi}`
              : `https://openalex.org/${graph.selected.value.openalex_id}`
          "
          target="_blank"
          rel="noopener"
          class="leading-snug font-medium hover:underline"
          >{{ graph.selected.value.title }}</a
        >
        <span v-else class="leading-snug font-medium">{{ graph.selected.value.title }}</span>
        <span class="text-xs text-surface-500">{{ meta() }}</span>
        <span class="text-xs text-surface-500">
          <template v-if="graph.selected.value.cited_by_count !== null">피인용 {{ graph.selected.value.cited_by_count.toLocaleString() }}</template>
          <template v-if="graph.selected.value.score !== null"> · 추천 점수 {{ graph.selected.value.score.toFixed(2) }}</template>
          <template v-if="graph.selected.value.paper_id !== null && !graph.selected.value.has_data"> · 인용 데이터 없음</template>
        </span>
        <Message v-if="graph.state.addError" severity="error" size="small">{{ graph.state.addError }}</Message>
      </div>
      <div class="flex shrink-0 items-center gap-1">
        <Button
          v-if="graph.selected.value.paper_id !== null"
          label="서재에서 보기"
          icon="pi pi-book"
          size="small"
          text
          @click="emit('open', graph.selected.value.paper_id)"
        />
        <Button
          v-else
          label="서재에 담기"
          icon="pi pi-plus"
          size="small"
          text
          :loading="graph.state.adding"
          @click="graph.add(graph.selected.value)"
        />
        <Button icon="pi pi-times" size="small" text severity="secondary" aria-label="닫기" @click="graph.select(null)" />
      </div>
    </div>
  </section>
</template>
