// @doc: docs/design/DriveSync.md#9-테스트

import { afterEach, describe, expect, it, vi } from 'vitest'
import type { DriveStatus } from './api'
import { createDriveState, syncedLabel } from './driveState'

function status(fields: Partial<DriveStatus> = {}): DriveStatus {
  return { state: 'idle', message: '', last_synced_at: null, pending: false, data_version: 0, ...fields }
}

function setup(responses: DriveStatus[] = [status()]) {
  const onDataChanged = vi.fn()
  const deps = {
    fetchDriveStatus: vi.fn(async () => responses.shift() ?? status()),
    syncDrive: vi.fn(async () => status({ data_version: 1 })),
    resolveDrive: vi.fn(async () => status()),
    disconnectDrive: vi.fn(async () => status({ state: 'disconnected' })),
  }
  return { drive: createDriveState(onDataChanged, deps), deps, onDataChanged }
}

afterEach(() => {
  vi.useRealTimers()
})

describe('createDriveState', () => {
  it('처음 불러오고, 빠르게 또는 느리게 다시 불러온다', async () => {
    vi.useFakeTimers()
    const { drive, deps } = setup([status({ pending: true }), status(), status()])
    await drive.start()
    expect(drive.state.status?.pending).toBe(true)
    await vi.advanceTimersByTimeAsync(2000)
    expect(deps.fetchDriveStatus).toHaveBeenCalledTimes(2)
    await vi.advanceTimersByTimeAsync(2000)
    expect(deps.fetchDriveStatus).toHaveBeenCalledTimes(2)
    await vi.advanceTimersByTimeAsync(8000)
    expect(deps.fetchDriveStatus).toHaveBeenCalledTimes(3)
    drive.stop()
    await vi.advanceTimersByTimeAsync(20000)
    expect(deps.fetchDriveStatus).toHaveBeenCalledTimes(3)
  })

  it('data_version이 바뀌면 콜백을 부른다', async () => {
    const { drive, onDataChanged } = setup([status({ data_version: 0 })])
    await drive.refresh()
    expect(onDataChanged).not.toHaveBeenCalled()
    await drive.syncNow()
    expect(onDataChanged).toHaveBeenCalledTimes(1)
  })

  it('동작 뒤 상태를 바꾸고, 실패하면 오류를 담는다', async () => {
    const { drive, deps } = setup()
    await drive.disconnect()
    expect(drive.state.status?.state).toBe('disconnected')
    await drive.resolve('local')
    expect(deps.resolveDrive).toHaveBeenCalledWith('local')
    deps.syncDrive.mockRejectedValueOnce(new Error('드라이브 요청 실패: 500'))
    await drive.syncNow()
    expect(drive.state.error).toBe('드라이브 요청 실패: 500')
    expect(drive.state.busy).toBe(false)
  })
})

describe('syncedLabel', () => {
  it('대기 중이면 올릴 변경, 아니면 마지막 동기화 시각을 보여 준다', () => {
    expect(syncedLabel(status({ pending: true }))).toBe('올릴 변경 있음')
    expect(syncedLabel(status())).toBe('드라이브 동기화됨')
    expect(syncedLabel(status({ last_synced_at: '2026-11-01T07:05:00+00:00' }))).toMatch(
      /^드라이브 동기화됨 · 11-01 \d\d:05$/,
    )
  })
})
