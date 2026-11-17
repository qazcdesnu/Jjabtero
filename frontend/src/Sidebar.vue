<!-- @doc: docs/design/UiLayout.md#3-화면-배치 -->
<!-- @doc: docs/design/LibraryFilter.md#4-화면 -->
<!-- @doc: docs/design/Tags.md#4-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Menu from 'primevue/menu'
import Message from 'primevue/message'
import { ref } from 'vue'
import { createLibraryState } from './libraryState'
import { VIEWS } from './navigation'

const props = defineProps<{ library: ReturnType<typeof createLibraryState> }>()
const view = defineModel<string>({ required: true })

function pickTag(name: string) {
  props.library.toggleTag(name)
  // 그래프 화면에서는 그래프를 고른 태그로 다시 그린다. 그 밖의 화면에서는 서재로 간다.
  if (view.value !== 'graph') view.value = 'library'
}

// 태그 메뉴: 이름 바꾸기, 지우기
const menu = ref<InstanceType<typeof Menu> | null>(null)
const target = ref<{ name: string; count: number } | null>(null)
const renaming = ref(false)
const deleting = ref(false)
const newName = ref('')
const menuItems = [
  {
    label: '이름 바꾸기',
    icon: 'pi pi-pencil',
    command: () => {
      newName.value = target.value?.name ?? ''
      renaming.value = true
    },
  },
  { label: '지우기', icon: 'pi pi-trash', command: () => (deleting.value = true) },
]

function openMenu(event: Event, tag: { name: string; count: number }) {
  target.value = tag
  props.library.state.tagError = ''
  menu.value?.toggle(event)
}

async function rename() {
  if (target.value && newName.value.trim() && (await props.library.renameTagEverywhere(target.value.name, newName.value)))
    renaming.value = false
}

async function remove() {
  if (target.value && (await props.library.deleteTagEverywhere(target.value.name))) deleting.value = false
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
    <div
      v-for="tag in library.tags.value"
      :key="tag.name"
      class="group flex items-center rounded-md text-sm transition-colors"
      :class="
        library.state.filter.tags.includes(tag.name)
          ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-200'
          : 'hover:bg-surface-100 dark:hover:bg-surface-800'
      "
    >
      <button
        type="button"
        class="flex min-w-0 flex-1 items-center justify-between gap-2 px-3 py-1.5 text-left"
        @click="pickTag(tag.name)"
      >
        <span class="flex min-w-0 items-center gap-2">
          <i class="pi pi-tag text-xs" />
          <span class="truncate">{{ tag.name }}</span>
        </span>
        <span class="text-xs text-surface-500 tabular-nums">{{ tag.count }}</span>
      </button>
      <button
        type="button"
        class="mr-1 rounded px-1 py-1 text-surface-400 opacity-0 group-hover:opacity-100 hover:text-surface-700 focus:opacity-100 dark:hover:text-surface-100"
        :aria-label="`${tag.name} 태그 메뉴`"
        @click="openMenu($event, tag)"
      >
        <i class="pi pi-ellipsis-v text-xs" />
      </button>
    </div>
    <Menu ref="menu" :model="menuItems" popup />

    <Dialog v-model:visible="renaming" modal header="태그 이름 바꾸기" :style="{ width: '22rem' }">
      <div class="flex flex-col gap-3">
        <p class="text-sm text-surface-500">같은 이름의 태그가 이미 있으면 두 태그를 합칩니다.</p>
        <InputText v-model="newName" aria-label="새 태그 이름" fluid autofocus @keydown.enter.prevent="rename" />
        <Message v-if="library.state.tagError" severity="error" size="small">{{ library.state.tagError }}</Message>
        <div class="flex justify-end gap-2">
          <Button label="취소" severity="secondary" text @click="renaming = false" />
          <Button label="바꾸기" :disabled="!newName.trim()" @click="rename" />
        </div>
      </div>
    </Dialog>
    <Dialog v-model:visible="deleting" modal header="태그 지우기" :style="{ width: '22rem' }">
      <div class="flex flex-col gap-3">
        <p class="text-sm">'{{ target?.name }}' 태그를 {{ target?.count }}편에서 뗍니다. 논문은 지우지 않습니다.</p>
        <Message v-if="library.state.tagError" severity="error" size="small">{{ library.state.tagError }}</Message>
        <div class="flex justify-end gap-2">
          <Button label="취소" severity="secondary" text @click="deleting = false" />
          <Button label="지우기" severity="danger" @click="remove" />
        </div>
      </div>
    </Dialog>
  </nav>
</template>
