<!-- @doc: docs/design/Reader.md#6-화면 -->
<!-- @doc: docs/design/Reader.md#1-뷰어-라이브러리 -->
<script setup lang="ts">
import 'pdfjs-dist/web/pdf_viewer.css'
import {
  GlobalWorkerOptions,
  TextLayer,
  getDocument,
  type PDFDocumentLoadingTask,
  type PDFDocumentProxy,
  type RenderTask,
} from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import { computed, nextTick, onMounted, onUnmounted, ref, shallowRef } from 'vue'
import { pdfUrl } from './api'
import {
  clampPage,
  fitWidthScale,
  nextZoom,
  PAGE_GAP,
  pageAt,
  pageTops,
  scrollTopFor,
  visiblePages,
  type PageSize,
} from './readerState'

GlobalWorkerOptions.workerSrc = workerUrl

const props = defineProps<{ paperId: number; title: string }>()
const emit = defineEmits<{ close: [] }>()

const scroller = ref<HTMLElement | null>(null)
const pageElements = ref<HTMLElement[]>([])
const doc = shallowRef<PDFDocumentProxy | null>(null)
const sizes = ref<PageSize[]>([])
const scale = ref(1)
const current = ref(1)
const loading = ref(true)
const failure = ref('')
let loadingTask: PDFDocumentLoadingTask | null = null
const rendered = new Map<number, number>()
const tasks = new Map<number, RenderTask>()
const textLayers = new Map<number, TextLayer>()

const tops = computed(() => pageTops(sizes.value, scale.value))
const heights = computed(() => sizes.value.map((size) => size.height * scale.value))
const total = computed(() => sizes.value.length)
const zoomLabel = computed(() => `${Math.round(scale.value * 100)}%`)

function clearPage(page: number) {
  tasks.get(page)?.cancel()
  tasks.delete(page)
  textLayers.get(page)?.cancel()
  textLayers.delete(page)
  rendered.delete(page)
  const element = pageElements.value[page - 1]
  if (!element) return
  const canvas = element.querySelector('canvas')
  if (canvas) {
    canvas.width = 0
    canvas.height = 0
  }
  element.querySelector('.textLayer')?.replaceChildren()
}

async function renderPage(page: number) {
  const pdf = doc.value
  const element = pageElements.value[page - 1]
  if (!pdf || !element || rendered.get(page) === scale.value) return
  clearPage(page)
  rendered.set(page, scale.value)
  const pdfPage = await pdf.getPage(page)
  const viewport = pdfPage.getViewport({ scale: scale.value })
  const ratio = window.devicePixelRatio || 1
  const canvas = element.querySelector('canvas') as HTMLCanvasElement
  canvas.width = Math.floor(viewport.width * ratio)
  canvas.height = Math.floor(viewport.height * ratio)
  canvas.style.width = `${viewport.width}px`
  canvas.style.height = `${viewport.height}px`
  const task = pdfPage.render({ canvas, viewport: pdfPage.getViewport({ scale: scale.value * ratio }) })
  tasks.set(page, task)
  try {
    await task.promise
  } catch {
    return
  }
  const container = element.querySelector('.textLayer') as HTMLElement
  const textLayer = new TextLayer({ textContentSource: pdfPage.streamTextContent(), container, viewport })
  textLayers.set(page, textLayer)
  try {
    await textLayer.render()
  } catch {
    // 다시 그리느라 취소된 경우다.
  }
}

function update() {
  const element = scroller.value
  if (!element || total.value === 0) return
  // 쪽 사이 간격만큼 아래를 보아, 쪽 머리 바로 위로 이동했을 때도 그 쪽으로 센다.
  current.value = pageAt(element.scrollTop + PAGE_GAP, tops.value)
  const wanted = visiblePages(element.scrollTop, element.clientHeight, tops.value, heights.value)
  for (const page of [...rendered.keys()]) {
    if (!wanted.some((near) => Math.abs(near - page) <= 2)) clearPage(page)
  }
  for (const page of wanted) void renderPage(page)
}

async function setScale(next: number) {
  const element = scroller.value
  if (!element || next === scale.value) return
  const anchor = current.value
  const offset = (element.scrollTop - tops.value[anchor - 1]) / (heights.value[anchor - 1] || 1)
  scale.value = next
  await nextTick()
  element.scrollTop = scrollTopFor(anchor, offset, tops.value, heights.value)
  update()
}

function goTo(page: number | null) {
  const element = scroller.value
  if (!element || page === null) return
  element.scrollTop = tops.value[clampPage(page, total.value) - 1] - 8
  update()
}

function fitWidth() {
  if (scroller.value) void setScale(fitWidthScale(sizes.value, scroller.value.clientWidth))
}

onMounted(async () => {
  try {
    loadingTask = getDocument({ url: pdfUrl(props.paperId), withCredentials: true })
    const pdf = await loadingTask.promise
    const found: PageSize[] = []
    for (let page = 1; page <= pdf.numPages; page += 1) {
      const viewport = (await pdf.getPage(page)).getViewport({ scale: 1 })
      found.push({ width: viewport.width, height: viewport.height })
    }
    doc.value = pdf
    sizes.value = found
    loading.value = false
    await nextTick()
    if (scroller.value) scale.value = Math.min(fitWidthScale(found, scroller.value.clientWidth), 1.5)
    await nextTick()
    update()
  } catch (error) {
    loading.value = false
    failure.value = `PDF를 열지 못했습니다: ${error instanceof Error ? error.message : String(error)}`
  }
})

onUnmounted(() => {
  for (const page of [...rendered.keys()]) clearPage(page)
  void loadingTask?.destroy()
})
</script>

<template>
  <section class="flex h-full flex-col bg-surface-100 dark:bg-surface-900">
    <header
      class="flex flex-wrap items-center gap-2 border-b border-surface-200 bg-surface-0 px-3 py-2 dark:border-surface-700 dark:bg-surface-900"
    >
      <Button icon="pi pi-arrow-left" text rounded aria-label="리더 닫기" @click="emit('close')" />
      <h2 class="min-w-0 flex-1 truncate font-medium" :title="title">{{ title }}</h2>
      <div class="flex items-center gap-1">
        <Button icon="pi pi-chevron-up" text rounded aria-label="이전 쪽" :disabled="current <= 1" @click="goTo(current - 1)" />
        <InputNumber
          :model-value="current"
          :min="1"
          :max="total || 1"
          :use-grouping="false"
          input-class="w-14 text-center"
          aria-label="쪽 번호"
          @update:model-value="goTo"
        />
        <span class="text-sm text-surface-500 tabular-nums">/ {{ total }}</span>
        <Button icon="pi pi-chevron-down" text rounded aria-label="다음 쪽" :disabled="current >= total" @click="goTo(current + 1)" />
      </div>
      <div class="flex items-center gap-1">
        <Button icon="pi pi-search-minus" text rounded aria-label="축소" @click="setScale(nextZoom(scale, -1))" />
        <span class="w-12 text-center text-sm tabular-nums">{{ zoomLabel }}</span>
        <Button icon="pi pi-search-plus" text rounded aria-label="확대" @click="setScale(nextZoom(scale, 1))" />
        <Button label="너비 맞춤" size="small" text @click="fitWidth" />
      </div>
    </header>

    <div ref="scroller" class="relative min-h-0 flex-1 overflow-auto" @scroll.passive="update">
      <p v-if="loading" class="p-6 text-center text-surface-500">PDF를 여는 중…</p>
      <Message v-if="failure" severity="error" class="m-6">{{ failure }}</Message>
      <div
        v-for="(size, index) in sizes"
        :key="index"
        ref="pageElements"
        class="reader-page relative mx-auto bg-white shadow"
        :style="{
          width: `${size.width * scale}px`,
          height: `${size.height * scale}px`,
          marginTop: index === 0 ? '16px' : '0',
          marginBottom: '16px',
          '--scale-factor': scale,
          '--total-scale-factor': scale,
          '--user-unit': 1,
        }"
        :data-page="index + 1"
      >
        <canvas class="absolute inset-0" />
        <div class="textLayer" />
      </div>
    </div>
  </section>
</template>
