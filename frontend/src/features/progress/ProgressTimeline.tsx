/** The progress history, newest first: "600 → 850 (+250)", who logged it, when, and any note. */
import { History, Undo2 } from 'lucide-react'
import { useState } from 'react'

import Badge from '../../components/Badge'
import Button from '../../components/Button'
import ConfirmDialog from '../../components/ConfirmDialog'
import { EmptyState } from '../../components/StatePanels'
import { errorMessageOf, useToast } from '../../components/toast/useToast'
import { formatNumber, formatSignedNumber, formatTimestamp } from '../../lib/format'
import type { ProgressUpdate } from './types'
import { useDeleteProgressUpdate } from './useProgress'

function ChangeChip({ change }: { change: number }) {
  return <Badge tone={change >= 0 ? 'success' : 'danger'}>{formatSignedNumber(change)}</Badge>
}

function TimelineEntry({ entry, unit, onUndo }: { entry: ProgressUpdate; unit: string; onUndo: () => void }) {
  return (
    <li className="relative border-l-2 border-stone-200 pb-5 pl-5 last:pb-0">
      <span aria-hidden className="absolute top-1.5 -left-[7px] size-3 rounded-full border-2 border-white bg-forest-500" />
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-semibold text-stone-900">
          {formatNumber(entry.previous_value)} → {formatNumber(entry.value)} {unit}
        </p>
        <ChangeChip change={entry.change} />
        {entry.is_correction && (
          <Badge tone="warning">Correction</Badge>
        )}
      </div>
      <p className="mt-0.5 text-sm text-stone-500">
        {entry.author.name} · {formatTimestamp(entry.recorded_at)}
      </p>
      {entry.note && <p className="mt-1 text-sm whitespace-pre-line text-stone-700">“{entry.note}”</p>}
      {entry.can_delete && (
        <Button variant="ghost" onClick={onUndo} className="mt-1 -ml-3 text-red-700">
          <Undo2 aria-hidden className="size-4" />
          Undo this update
        </Button>
      )}
    </li>
  )
}

export default function ProgressTimeline({
  projectId,
  history,
  unit,
}: {
  projectId: number
  history: ProgressUpdate[]
  unit: string
}) {
  const [entryToUndo, setEntryToUndo] = useState<ProgressUpdate | null>(null)
  const deleteUpdate = useDeleteProgressUpdate(projectId)
  const { showToast } = useToast()

  if (history.length === 0) {
    return <EmptyState icon={History} title="No progress logged yet" description="Each update will appear here." />
  }

  async function confirmUndo() {
    if (!entryToUndo) return
    try {
      await deleteUpdate.mutateAsync(entryToUndo.id)
      showToast('success', `Update undone. The total is back to ${formatNumber(entryToUndo.previous_value)} ${unit}.`)
    } catch (error) {
      showToast('error', errorMessageOf(error, 'Could not undo the update.'))
    } finally {
      setEntryToUndo(null)
    }
  }

  return (
    <>
      <ol aria-label="Progress history, newest first" className="ml-1.5">
        {history.map((entry) => (
          <TimelineEntry key={entry.id} entry={entry} unit={unit} onUndo={() => setEntryToUndo(entry)} />
        ))}
      </ol>
      <ConfirmDialog
        open={entryToUndo !== null}
        title="Undo the latest update?"
        confirmLabel="Undo update"
        isConfirming={deleteUpdate.isPending}
        onConfirm={() => void confirmUndo()}
        onCancel={() => setEntryToUndo(null)}
      >
        {entryToUndo && (
          <p>
            The entry {formatNumber(entryToUndo.previous_value)} → {formatNumber(entryToUndo.value)} will be removed and
            the total goes back to {formatNumber(entryToUndo.previous_value)}.
          </p>
        )}
      </ConfirmDialog>
    </>
  )
}
