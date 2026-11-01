<!-- @doc: docs/design/DriveSync.md#7-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Menu from 'primevue/menu'
import Tag from 'primevue/tag'
import { computed, ref } from 'vue'
import { driveConnectUrl } from './api'
import { createDriveState, syncedLabel } from './driveState'

const props = defineProps<{ drive: ReturnType<typeof createDriveState> }>()
const status = computed(() => props.drive.state.status)
const menu = ref<InstanceType<typeof Menu> | null>(null)
const conflictOpen = ref(false)

const menuItems = [
  { label: '지금 동기화', icon: 'pi pi-sync', command: () => props.drive.syncNow() },
  { label: '연결 해제', icon: 'pi pi-sign-out', command: () => props.drive.disconnect() },
]

function connect() {
  window.location.href = driveConnectUrl(window.location.href)
}

async function resolve(choice: 'remote' | 'local') {
  await props.drive.resolve(choice)
  conflictOpen.value = false
}
</script>

<template>
  <div class="flex items-center gap-2 text-sm">
    <template v-if="!status">
      <Tag severity="secondary" value="드라이브 확인 중" />
    </template>
    <template v-else-if="status.state === 'not_configured'">
      <Tag v-tooltip.bottom="status.message" severity="secondary" icon="pi pi-cloud" value="드라이브 설정 안 됨" />
    </template>
    <template v-else-if="status.state === 'disconnected'">
      <span v-if="status.message" class="text-xs text-surface-500">{{ status.message }}</span>
      <Button label="드라이브 연결" icon="pi pi-cloud" size="small" outlined @click="connect" />
    </template>
    <template v-else>
      <Tag v-if="status.state === 'syncing'" severity="info" icon="pi pi-spin pi-sync" value="동기화 중" />
      <Tag v-else-if="status.state === 'idle'" severity="success" icon="pi pi-cloud" :value="syncedLabel(status)" />
      <template v-else-if="status.state === 'error'">
        <Tag v-tooltip.bottom="status.message" severity="danger" icon="pi pi-exclamation-circle" value="동기화 오류" />
        <Button label="다시 시도" size="small" text :loading="drive.state.busy" @click="drive.syncNow()" />
      </template>
      <Button
        v-else-if="status.state === 'conflict'"
        label="충돌"
        icon="pi pi-exclamation-triangle"
        severity="warn"
        size="small"
        @click="conflictOpen = true"
      />
      <Button
        icon="pi pi-ellipsis-v"
        severity="secondary"
        text
        rounded
        size="small"
        aria-label="드라이브 메뉴"
        @click="menu?.toggle($event)"
      />
      <Menu ref="menu" :model="menuItems" popup />
    </template>
    <span v-if="drive.state.error" class="text-xs text-red-500">{{ drive.state.error }}</span>

    <Dialog v-model:visible="conflictOpen" modal header="서재 충돌" class="w-[28rem]">
      <p class="mb-2">{{ status?.message }}</p>
      <p class="mb-4 text-sm text-surface-500">
        고르지 않은 쪽은 서재 파일 옆 <code>backups</code> 폴더에 백업으로 남습니다.
      </p>
      <div class="flex justify-end gap-2">
        <Button label="드라이브 것 쓰기" icon="pi pi-cloud-download" outlined :loading="drive.state.busy" @click="resolve('remote')" />
        <Button label="이 컴퓨터 것 쓰기" icon="pi pi-cloud-upload" :loading="drive.state.busy" @click="resolve('local')" />
      </div>
    </Dialog>
  </div>
</template>
