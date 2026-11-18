<!-- @doc: docs/design/Tags.md#5-태그별-그래프 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import { computed } from 'vue'

// title: 담을 논문 제목. tags: 고른 태그 전체. 체크한 태그는 v-model:chosen이다.
const props = defineProps<{ title: string | null; tags: string[] }>()
const chosen = defineModel<string[]>('chosen', { required: true })
const emit = defineEmits<{ confirm: []; cancel: [] }>()

const visible = computed({
  get: () => props.title !== null,
  set: (open: boolean) => {
    if (!open) emit('cancel')
  },
})
</script>

<template>
  <Dialog v-model:visible="visible" modal header="서재에 담기" :style="{ width: '28rem' }" :breakpoints="{ '640px': '95vw' }">
    <p class="mb-1 text-sm font-medium leading-snug">{{ title }}</p>
    <p class="mb-3 text-sm text-surface-600 dark:text-surface-300">선택된 태그를 이 논문에도 추가하시겠습니까? 추가할 태그를 고르세요.</p>
    <div class="flex flex-col gap-2">
      <label v-for="tag in tags" :key="tag" class="flex items-center gap-2 text-sm">
        <Checkbox v-model="chosen" :value="tag" :input-id="`graph-add-tag-${tag}`" />
        <span>{{ tag }}</span>
      </label>
    </div>
    <template #footer>
      <Button label="담기 취소" severity="secondary" text @click="emit('cancel')" />
      <Button label="서재에 담기" icon="pi pi-plus" @click="emit('confirm')" />
    </template>
  </Dialog>
</template>
