<!-- @doc: docs/design/Reader.md#6-화면 -->
<!-- @doc: docs/design/Reader.md#1-뷰어-라이브러리 -->
<!-- @doc: docs/design/ReaderCitations.md#2-인용-표시-찾기 -->
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
import Textarea from 'primevue/textarea'
import { computed, nextTick, onMounted, onUnmounted, ref, shallowRef } from 'vue'
import {
  createAnnotation,
  deleteAnnotation,
  fetchPosition,
  listAnnotations,
  pdfUrl,
  savePosition,
  updateAnnotation,
  type Annotation,
} from './api'
import {
  HIGHLIGHT_COLORS,
  annotationSummary,
  colorFill,
  dragRect,
  hitTest,
  normalizeRects,
  type Rect,
} from './annotations'
import {
  anchorFromDest,
  isCitationDest,
  linkRect,
  referenceEntryText,
  type Anchor,
  type CitationLink,
  type TextPiece,
} from './citationLinks'
import { createReferencePreview } from './referencePreview'
import { findMarkers, hasReferenceHeading, referenceEntries, type PageText, type ReferenceEntry } from './textCitations'
import ReferencePreview from './ReferencePreview.vue'
import {
  clampPage,
  createPositionSaver,
  fitWidthScale,
  nextZoom,
  notePlacement,
  NOTE_BOX_WIDTH,
  PAGE_GAP,
  pageAt,
  pageTops,
  positionAt,
  scrollTopFor,
  visiblePages,
  type PageSize,
} from './readerState'

GlobalWorkerOptions.workerSrc = workerUrl

const props = defineProps<{ paperId: number; title: string }>()
const emit = defineEmits<{ close: []; added: [] }>()

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
const saver = createPositionSaver((position: { page: number; offset: number; zoom: number }) =>
  savePosition(props.paperId, position),
)
let restored = false

const annotations = ref<Annotation[]>([])
const annotationError = ref('')
const pending = ref<{ page: number; rects: Rect[]; text: string; left: number; top: number } | null>(null)
const editing = ref<{ annotation: Annotation; note: string; left: number; top: number } | null>(null)
const noteMode = ref(false)
const dragging = ref<{ page: number; start: { x: number; y: number }; current: { x: number; y: number } } | null>(null)
const drafting = ref<{ page: number; rect: Rect; note: string; left: number; top: number } | null>(null)
const listOpen = ref(false)
const dragPreview = computed(() => (dragging.value ? dragRect(dragging.value.start, dragging.value.current) : null))

// 인용 링크(쪽마다)와 참고문헌 목적지. 링크 위에 요소를 겹치지 않고 마우스 위치로 확인한다.
const citationLinks = new Map<number, CitationLink[]>()
const pageTexts = new Map<number, Promise<{ pieces: TextPiece[]; right: number; view: number[] }>>()
let anchorsPromise: Promise<Map<string, Anchor>> | null = null
// 링크가 없는 PDF는 글자로 참고문헌과 인용 표시를 찾는다. 인용 링크의 목적지를 하나라도 찾을 수 있으면 쓰지 않는다.
// 학술지가 다시 저장한 PDF는 인용 링크만 남고 목적지가 모두 사라지기도 한다(이슈 H4).
let textIndexPromise: Promise<ReferenceEntry[]> | null = null
const TEXT_DEST = 'text:'
const hoveredLink = ref<CitationLink | null>(null)
const preview = createReferencePreview(props.paperId, entryText, () => emit('added'))

async function readCitationLinks(page: number): Promise<void> {
  const pdf = doc.value
  if (!pdf || citationLinks.has(page)) return
  citationLinks.set(page, [])
  const pdfPage = await pdf.getPage(page)
  const viewport = pdfPage.getViewport({ scale: 1 })
  const found: CitationLink[] = []
  for (const annotation of await pdfPage.getAnnotations()) {
    if (annotation.subtype !== 'Link' || !isCitationDest(annotation.dest)) continue
    const [x1, y1, x2, y2] = annotation.rect as number[]
    const corners = [...viewport.convertToViewportPoint(x1, y1), ...viewport.convertToViewportPoint(x2, y2)] as number[]
    const rect = linkRect(corners, viewport.width, viewport.height)
    found.push({ page, dest: annotation.dest, rects: [rect] })
  }
  if (found.length > 0 && (await readAnchors()).size === 0) found.length = 0
  if (found.length === 0) {
    const entries = await readTextIndex()
    if (entries.length) {
      const text = await readPageText(page)
      for (const marker of findMarkers(asPageText(page, text), entries, measureText)) {
        found.push({ page, dest: `${TEXT_DEST}${marker.entry}`, rects: marker.rects })
      }
    }
  }
  citationLinks.set(page, found)
}

// 인용 표시의 영역을 글자의 실제 너비 비율로 잡기 위해 캔버스로 잰다. 글꼴 크기는 비율만 쓰므로 상관없다.
const measureCanvas = document.createElement('canvas').getContext('2d')
function measureText(text: string, font = 'serif'): number {
  if (!measureCanvas) return text.length
  measureCanvas.font = `100px ${font}`
  return measureCanvas.measureText(text).width
}

function asPageText(page: number, text: { pieces: TextPiece[]; view: number[] }): PageText {
  return {
    page,
    view: text.view,
    pieces: text.pieces.map((piece) => ({ ...piece, width: piece.width ?? 0, height: piece.height ?? 0 })),
  }
}

function readTextIndex(): Promise<ReferenceEntry[]> {
  textIndexPromise ??= (async () => {
    const pdf = doc.value!
    if ((await readAnchors()).size > 0) {
      for (let page = 1; page <= pdf.numPages; page += 1) {
        const annotations = await (await pdf.getPage(page)).getAnnotations()
        if (annotations.some((annotation) => annotation.subtype === 'Link' && isCitationDest(annotation.dest))) return []
      }
    }
    // 참고문헌은 대개 끝에 있으므로 뒤에서부터 제목을 찾는다.
    for (let page = pdf.numPages; page >= 1; page -= 1) {
      if (!hasReferenceHeading(asPageText(page, await readPageText(page)))) continue
      const pages: PageText[] = []
      for (let next = page; next <= pdf.numPages; next += 1) pages.push(asPageText(next, await readPageText(next)))
      return referenceEntries(pages)
    }
    return []
  })()
  return textIndexPromise
}

function readAnchors(): Promise<Map<string, Anchor>> {
  anchorsPromise ??= (async () => {
    const pdf = doc.value!
    const anchors = new Map<string, Anchor>()
    const pages = new Map<string, number>()
    const destinations = (await pdf.getDestinations()) as unknown as Map<string, unknown[]> | Record<string, unknown[]>
    const entries = destinations instanceof Map ? [...destinations.entries()] : Object.entries(destinations)
    for (const [name, dest] of entries) {
      if (!isCitationDest(name) || !Array.isArray(dest) || !dest[0] || typeof dest[0] !== 'object') continue
      const ref = dest[0] as { num: number; gen: number }
      const key = `${ref.num}R${ref.gen}`
      if (!pages.has(key)) pages.set(key, (await pdf.getPageIndex(ref)) + 1)
      anchors.set(name, anchorFromDest(name, pages.get(key)!, dest))
    }
    return anchors
  })()
  return anchorsPromise
}

function readPageText(page: number) {
  let found = pageTexts.get(page)
  if (!found) {
    found = (async () => {
      const pdfPage = await doc.value!.getPage(page)
      const content = await pdfPage.getTextContent()
      const pieces = content.items.flatMap((item) =>
        'str' in item
          ? [
              {
                str: item.str,
                x: item.transform[4] as number,
                y: item.transform[5] as number,
                width: item.width,
                height: item.height,
                font: content.styles[item.fontName]?.fontFamily,
              },
            ]
          : [],
      )
      return { pieces, right: pdfPage.view[2], view: pdfPage.view }
    })()
    pageTexts.set(page, found)
  }
  return found
}

async function entryText(dest: string): Promise<string> {
  if (dest.startsWith(TEXT_DEST)) {
    const entry = (await readTextIndex())[Number(dest.slice(TEXT_DEST.length))]
    return entry ? entry.text.slice(0, 600) : ''
  }
  const anchors = await readAnchors()
  const anchor = anchors.get(dest)
  if (!anchor) return ''
  const { pieces, right } = await readPageText(anchor.page)
  return referenceEntryText(anchor, [...anchors.values()], pieces, right)
}

async function goToDest(dest: string) {
  if (dest.startsWith(TEXT_DEST)) {
    const entry = (await readTextIndex())[Number(dest.slice(TEXT_DEST.length))]
    const element = scroller.value
    if (!entry || !element) return
    const [, bottom, , top] = (await doc.value!.getPage(entry.page)).view
    const offset = (top - entry.y) / (top - bottom || 1)
    element.scrollTop = Math.max(tops.value[entry.page - 1] + offset * heights.value[entry.page - 1] - 40, 0)
    update()
    return
  }
  const element = scroller.value
  const anchor = (await readAnchors()).get(dest)
  if (!element || !anchor) return
  const pdfPage = await doc.value!.getPage(anchor.page)
  const [, bottom, , top] = pdfPage.view
  const offset = anchor.y === null ? 0 : (top - anchor.y) / (top - bottom || 1)
  element.scrollTop = Math.max(tops.value[anchor.page - 1] + offset * heights.value[anchor.page - 1] - 40, 0)
  update()
}

function checkCitationHover(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (target.closest('.reader-popup')) return
  const pageElement = noteMode.value ? null : pageOf(target)
  const page = pageElement ? Number(pageElement.dataset.page) : 0
  const hit = pageElement ? hitTest(page, pagePoint(pageElement, event), citationLinks.get(page) ?? []) : null
  if (!hit) {
    if (hoveredLink.value) {
      hoveredLink.value = null
      preview.leave()
    }
    return
  }
  hoveredLink.value = hit
  const rect = hit.rects[0]
  const element = scroller.value!
  const linkTop = tops.value[page - 1] + rect.y * heights.value[page - 1]
  const linkBottom = linkTop + rect.h * heights.value[page - 1]
  // 아래 공간이 모자라면 위에 띄운다.
  const above = linkBottom + 260 > element.scrollTop + element.clientHeight
  preview.hover(hit.dest, {
    // 상자(너비 384px)가 오른쪽으로 넘치지 않게 한다.
    left: Math.max(
      Math.min(pageElement!.offsetLeft + rect.x * pageElement!.offsetWidth, element.scrollLeft + element.clientWidth - 392),
      8,
    ),
    top: above ? linkTop - 6 : linkBottom + 6,
    above,
  })
}

function pagePoint(pageElement: HTMLElement, event: MouseEvent) {
  const box = pageElement.getBoundingClientRect()
  return { x: (event.clientX - box.left) / box.width, y: (event.clientY - box.top) / box.height }
}

function onMouseDown(event: MouseEvent) {
  if (!noteMode.value || (event.target as HTMLElement).closest('.reader-popup')) return
  const pageElement = pageOf(event.target as Node)
  if (!pageElement) return
  event.preventDefault()
  const point = pagePoint(pageElement, event)
  dragging.value = { page: Number(pageElement.dataset.page), start: point, current: point }
  pending.value = null
  editing.value = null
  drafting.value = null
}

function onMouseMove(event: MouseEvent) {
  const drag = dragging.value
  if (!drag) {
    checkCitationHover(event)
    return
  }
  const pageElement = pageElements.value[drag.page - 1]
  if (pageElement) drag.current = pagePoint(pageElement, event)
}

function finishDrag(event: MouseEvent) {
  const drag = dragging.value
  dragging.value = null
  if (!drag) return
  const rect = dragRect(drag.start, drag.current)
  if (!rect) return
  drafting.value = { page: drag.page, rect, note: '', ...contentPoint(event.clientX, event.clientY) }
}

async function saveDraft() {
  const draft = drafting.value
  if (!draft) return
  try {
    const created = await createAnnotation(props.paperId, {
      kind: 'note',
      page: draft.page,
      rects: [draft.rect],
      color: 'yellow',
      note: draft.note,
    })
    annotations.value = [...annotations.value, created]
    drafting.value = null
    noteMode.value = false
    annotationError.value = ''
  } catch (error) {
    showError(error)
  }
}

function goToAnnotation(annotation: Annotation) {
  const element = scroller.value
  const pageElement = pageElements.value[annotation.page - 1]
  if (!element || !pageElement) return
  const rect = annotation.rects[0]
  const top = tops.value[annotation.page - 1] + rect.y * heights.value[annotation.page - 1]
  element.scrollTop = Math.max(top - 120, 0)
  update()
  editing.value = {
    annotation,
    note: annotation.note ?? '',
    left: pageElement.offsetLeft + rect.x * pageElement.offsetWidth,
    top: top + rect.h * heights.value[annotation.page - 1],
  }
  pending.value = null
}

const sortedAnnotations = computed(() =>
  [...annotations.value].sort((a, b) => a.page - b.page || a.rects[0].y - b.rects[0].y || a.id - b.id),
)

const byPage = computed(() => {
  const pages = new Map<number, Annotation[]>()
  for (const annotation of annotations.value) pages.set(annotation.page, [...(pages.get(annotation.page) ?? []), annotation])
  return pages
})

function contentPoint(clientX: number, clientY: number) {
  const element = scroller.value as HTMLElement
  const box = element.getBoundingClientRect()
  return { left: clientX - box.left + element.scrollLeft, top: clientY - box.top + element.scrollTop }
}

function pageOf(node: Node | null): HTMLElement | null {
  const element = node instanceof Element ? node : node?.parentElement
  return element?.closest<HTMLElement>('.reader-page') ?? null
}

function showError(error: unknown) {
  annotationError.value = error instanceof Error ? error.message : String(error)
}

function onMouseUp(event: MouseEvent) {
  if ((event.target as HTMLElement).closest('.reader-popup')) return
  if (dragging.value) {
    finishDrag(event)
    return
  }
  if (noteMode.value) return
  const selection = window.getSelection()
  if (selection && !selection.isCollapsed && selection.rangeCount > 0) {
    const range = selection.getRangeAt(0)
    const pageElement = pageOf(range.startContainer)
    if (!pageElement) return
    const rects = normalizeRects([...range.getClientRects()], pageElement.getBoundingClientRect())
    if (rects.length === 0) return
    const box = range.getBoundingClientRect()
    pending.value = {
      page: Number(pageElement.dataset.page),
      rects,
      text: selection.toString().trim(),
      ...contentPoint(box.left + box.width / 2, box.bottom),
    }
    editing.value = null
    return
  }
  pending.value = null
  if (hoveredLink.value) {
    // 글을 고르지 않고 인용 링크를 누르면 참고문헌 쪽으로 간다.
    void goToDest(hoveredLink.value.dest)
    preview.close()
    editing.value = null
    return
  }
  const pageElement = pageOf(event.target as Node)
  if (!pageElement) {
    editing.value = null
    return
  }
  const box = pageElement.getBoundingClientRect()
  const point = { x: (event.clientX - box.left) / box.width, y: (event.clientY - box.top) / box.height }
  const hit = hitTest(Number(pageElement.dataset.page), point, annotations.value)
  editing.value = hit ? { annotation: hit, note: hit.note ?? '', ...contentPoint(event.clientX, event.clientY) } : null
}

function replaceAnnotation(updated: Annotation) {
  annotations.value = annotations.value.map((annotation) => (annotation.id === updated.id ? updated : annotation))
  if (editing.value?.annotation.id === updated.id) editing.value.annotation = updated
}

async function addHighlight(color: string) {
  const target = pending.value
  if (!target) return
  try {
    const created = await createAnnotation(props.paperId, {
      kind: 'highlight',
      page: target.page,
      rects: target.rects,
      text: target.text,
      color,
    })
    annotations.value = [...annotations.value, created]
    window.getSelection()?.removeAllRanges()
    pending.value = null
    annotationError.value = ''
  } catch (error) {
    showError(error)
  }
}

async function changeColor(color: string) {
  const target = editing.value
  if (!target) return
  try {
    replaceAnnotation(await updateAnnotation(target.annotation.id, { color }))
  } catch (error) {
    showError(error)
  }
}

async function saveNote() {
  const target = editing.value
  if (!target) return
  try {
    replaceAnnotation(await updateAnnotation(target.annotation.id, { note: target.note }))
    editing.value = null
  } catch (error) {
    showError(error)
  }
}

async function removeAnnotation() {
  const target = editing.value
  if (!target) return
  try {
    await deleteAnnotation(target.annotation.id)
    annotations.value = annotations.value.filter((annotation) => annotation.id !== target.annotation.id)
    editing.value = null
  } catch (error) {
    showError(error)
  }
}

function onKeyDown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    preview.close()
    pending.value = null
    editing.value = null
    drafting.value = null
    dragging.value = null
    noteMode.value = false
  }
}

// 리더에서 지금 보이는 영역(내용 좌표). 메모 상자가 화면 아래를 넘지 않게 하는 데 쓴다.
const viewport = ref({ left: 0, top: 0, width: 0, height: 0 })
function measureViewport() {
  const element = scroller.value
  if (element)
    viewport.value = { left: element.scrollLeft, top: element.scrollTop, width: element.clientWidth, height: element.clientHeight }
}
const editingPlace = computed(() => (editing.value ? notePlacement(editing.value, viewport.value) : null))
const draftingPlace = computed(() => (drafting.value ? notePlacement(drafting.value, viewport.value) : null))
function boxStyle(place: { left: number; top: number; maxHeight: number } | null) {
  return place
    ? { left: `${place.left}px`, top: `${place.top}px`, maxHeight: `${place.maxHeight}px`, width: `${NOTE_BOX_WIDTH}px` }
    : {}
}

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
  void readCitationLinks(page)
}

function update() {
  measureViewport()
  const element = scroller.value
  if (!element || total.value === 0) return
  // 쪽 사이 간격만큼 아래를 보아, 쪽 머리 바로 위로 이동했을 때도 그 쪽으로 센다.
  current.value = pageAt(element.scrollTop + PAGE_GAP, tops.value)
  const wanted = visiblePages(element.scrollTop, element.clientHeight, tops.value, heights.value)
  for (const page of [...rendered.keys()]) {
    if (!wanted.some((near) => Math.abs(near - page) <= 2)) clearPage(page)
  }
  for (const page of wanted) void renderPage(page)
  if (restored)
    saver.schedule({ ...positionAt(element.scrollTop + PAGE_GAP, tops.value, heights.value), zoom: scale.value })
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
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('resize', measureViewport)
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
    const saved = await fetchPosition(props.paperId).catch(() => null)
    if (saved) scale.value = saved.zoom
    else if (scroller.value) scale.value = Math.min(fitWidthScale(found, scroller.value.clientWidth), 1.5)
    await nextTick()
    if (saved && scroller.value)
      scroller.value.scrollTop = scrollTopFor(saved.page, saved.offset, tops.value, heights.value) - PAGE_GAP
    restored = true
    update()
    annotations.value = await listAnnotations(props.paperId).catch((error) => {
      showError(error)
      return []
    })
  } catch (error) {
    loading.value = false
    failure.value = `PDF를 열지 못했습니다: ${error instanceof Error ? error.message : String(error)}`
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('resize', measureViewport)
  preview.close()
  void saver.flush()
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
      <div class="flex items-center gap-1">
        <Button
          icon="pi pi-stop"
          label="영역 메모"
          size="small"
          :text="!noteMode"
          :aria-pressed="noteMode"
          title="끌어서 영역을 고르고 메모를 답니다"
          @click="noteMode = !noteMode"
        />
        <Button
          icon="pi pi-list"
          :label="`주석 ${annotations.length}`"
          size="small"
          :text="!listOpen"
          :aria-pressed="listOpen"
          @click="listOpen = !listOpen"
        />
      </div>
    </header>

    <Message v-if="annotationError" severity="error" size="small" closable class="mx-3 mt-2" @close="annotationError = ''">
      {{ annotationError }}
    </Message>
    <div class="flex min-h-0 flex-1">
    <div
      ref="scroller"
      class="relative min-h-0 flex-1 overflow-auto"
      :class="{ 'reader-note-mode': noteMode, 'cursor-pointer': hoveredLink }"
      @scroll.passive="update"
      @mousedown="onMouseDown"
      @mousemove="onMouseMove"
      @mouseup="onMouseUp"
    >
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
        <div class="pointer-events-none absolute inset-0">
          <template v-for="annotation in byPage.get(index + 1) ?? []" :key="annotation.id">
            <template v-if="annotation.kind === 'highlight'">
              <div
                v-for="(rect, part) in annotation.rects"
                :key="part"
                class="reader-highlight absolute"
                :data-annotation="annotation.id"
                :style="{
                  left: `${rect.x * 100}%`,
                  top: `${rect.y * 100}%`,
                  width: `${rect.w * 100}%`,
                  height: `${rect.h * 100}%`,
                  background: colorFill(annotation.color),
                  mixBlendMode: 'multiply',
                }"
              />
            </template>
            <div
              v-else
              class="reader-note absolute rounded-sm border-2 border-amber-400"
              :data-annotation="annotation.id"
              :style="{
                left: `${annotation.rects[0].x * 100}%`,
                top: `${annotation.rects[0].y * 100}%`,
                width: `${annotation.rects[0].w * 100}%`,
                height: `${annotation.rects[0].h * 100}%`,
                background: 'rgba(250, 204, 21, 0.10)',
              }"
            >
              <i class="pi pi-comment absolute -top-3 -right-3 rounded-full bg-amber-400 p-1 text-xs text-white" />
            </div>
          </template>
          <div
            v-if="dragging && dragging.page === index + 1 && dragPreview"
            class="absolute border-2 border-dashed border-amber-500 bg-amber-200/20"
            :style="{
              left: `${dragPreview.x * 100}%`,
              top: `${dragPreview.y * 100}%`,
              width: `${dragPreview.w * 100}%`,
              height: `${dragPreview.h * 100}%`,
            }"
          />
        </div>
        <div class="textLayer" />
      </div>

      <div
        v-if="pending"
        class="reader-popup absolute z-20 flex -translate-x-1/2 gap-1 rounded-md border border-surface-200 bg-surface-0 p-1 shadow-lg dark:border-surface-700 dark:bg-surface-800"
        :style="{ left: `${pending.left}px`, top: `${pending.top + 6}px` }"
        @mousedown.prevent
      >
        <button
          v-for="color in HIGHLIGHT_COLORS"
          :key="color.name"
          type="button"
          class="h-6 w-6 rounded-full border border-surface-300"
          :style="{ background: color.fill }"
          :aria-label="`${color.label} 하이라이트`"
          :title="`${color.label} 하이라이트`"
          @click="addHighlight(color.name)"
        />
      </div>

      <div
        v-if="editing"
        class="reader-popup absolute z-20 flex max-w-[90vw] flex-col gap-2 rounded-md border border-surface-200 bg-surface-0 p-3 shadow-lg dark:border-surface-700 dark:bg-surface-800"
        :style="boxStyle(editingPlace)"
      >
        <p v-if="editing.annotation.text" class="line-clamp-3 shrink-0 text-xs text-surface-500">“{{ editing.annotation.text }}”</p>
        <span v-if="editing.annotation.kind === 'note'" class="shrink-0 text-xs text-surface-500">{{ editing.annotation.page }}쪽 영역 메모</span>
        <div v-else class="flex shrink-0 gap-1">
          <button
            v-for="color in HIGHLIGHT_COLORS"
            :key="color.name"
            type="button"
            class="h-6 w-6 rounded-full border"
            :class="editing.annotation.color === color.name ? 'border-surface-900 dark:border-surface-0' : 'border-surface-300'"
            :style="{ background: color.fill }"
            :aria-label="`${color.label}으로 바꾸기`"
            @click="changeColor(color.name)"
          />
        </div>
        <!-- 메모가 길면 이 칸 안에서 스크롤한다. 버튼은 늘 상자 아래에 보인다. -->
        <div class="min-h-0 flex-1 overflow-y-auto">
          <Textarea v-model="editing.note" rows="3" auto-resize placeholder="메모" aria-label="주석 메모" fluid />
        </div>
        <div class="flex shrink-0 justify-between gap-2">
          <Button label="삭제" icon="pi pi-trash" size="small" severity="danger" text @click="removeAnnotation" />
          <div class="flex gap-1">
            <Button label="닫기" size="small" severity="secondary" text @click="editing = null" />
            <Button label="메모 저장" size="small" @click="saveNote" />
          </div>
        </div>
      </div>

      <div
        v-if="drafting"
        class="reader-popup absolute z-20 flex max-w-[90vw] flex-col gap-2 rounded-md border border-surface-200 bg-surface-0 p-3 shadow-lg dark:border-surface-700 dark:bg-surface-800"
        :style="boxStyle(draftingPlace)"
      >
        <span class="shrink-0 text-xs text-surface-500">{{ drafting.page }}쪽 영역 메모</span>
        <div class="min-h-0 flex-1 overflow-y-auto">
          <Textarea v-model="drafting.note" rows="3" auto-resize placeholder="이 영역에 남길 메모" aria-label="영역 메모 내용" fluid autofocus />
        </div>
        <div class="flex shrink-0 justify-end gap-1">
          <Button label="취소" size="small" severity="secondary" text @click="drafting = null" />
          <Button label="저장" size="small" @click="saveDraft" />
        </div>
      </div>
      <ReferencePreview :preview="preview" />
    </div>

    <aside
      v-if="listOpen"
      class="flex w-72 shrink-0 flex-col overflow-auto border-l border-surface-200 bg-surface-0 dark:border-surface-700 dark:bg-surface-900"
      aria-label="주석 목록"
    >
      <p v-if="sortedAnnotations.length === 0" class="p-4 text-sm text-surface-500">
        글을 골라 하이라이트하거나 "영역 메모"로 메모를 남기면 여기에 모입니다.
      </p>
      <button
        v-for="annotation in sortedAnnotations"
        :key="annotation.id"
        type="button"
        class="flex gap-2 border-b border-surface-100 px-3 py-2 text-left text-sm hover:bg-surface-50 dark:border-surface-800 dark:hover:bg-surface-800"
        @click="goToAnnotation(annotation)"
      >
        <span
          class="mt-1 h-3 w-3 shrink-0 rounded-sm"
          :class="annotation.kind === 'note' ? 'border-2 border-amber-400' : ''"
          :style="annotation.kind === 'highlight' ? { background: colorFill(annotation.color) } : {}"
        />
        <span class="min-w-0 flex-1">
          <span class="block text-xs text-surface-500">{{ annotation.page }}쪽 · {{ annotation.kind === 'note' ? '영역 메모' : '하이라이트' }}</span>
          <span class="line-clamp-2">{{ annotationSummary(annotation) }}</span>
        </span>
      </button>
    </aside>
    </div>
  </section>
</template>

<style scoped>
.reader-note-mode {
  cursor: crosshair;
}
.reader-note-mode :deep(.textLayer) {
  pointer-events: none;
}
</style>

