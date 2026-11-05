/** A list of activity entries: an icon per action, the server's sentence, when, and a link to the project. */
import {
  FolderPlus,
  Pencil,
  Trash2,
  TrendingUp,
  Undo2,
  UserCheck,
  UserCog,
  UserX,
  type LucideIcon,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { formatRelativeTime, formatTimestamp } from '../../lib/format'
import { useNow } from '../../lib/useNow'
import type { ActivityAction, ActivityEntry } from './types'

const RELATIVE_TIME_REFRESH_MS = 60 * 1000

const ACTION_ICONS: Record<ActivityAction, { icon: LucideIcon; style: string }> = {
  created: { icon: FolderPlus, style: 'bg-forest-100 text-forest-800' },
  updated: { icon: Pencil, style: 'bg-sky-100 text-sky-800' },
  deleted: { icon: Trash2, style: 'bg-red-100 text-red-800' },
  progress_logged: { icon: TrendingUp, style: 'bg-forest-100 text-forest-800' },
  progress_deleted: { icon: Undo2, style: 'bg-amber-100 text-amber-900' },
  role_changed: { icon: UserCog, style: 'bg-violet-100 text-violet-800' },
  user_deactivated: { icon: UserX, style: 'bg-red-100 text-red-800' },
  user_activated: { icon: UserCheck, style: 'bg-forest-100 text-forest-800' },
}

function ProjectReference({ entry }: { entry: ActivityEntry }) {
  if (entry.project_id !== null) {
    return (
      <Link
        to={`/projects/${entry.project_id}`}
        className="font-medium break-words text-forest-700 hover:text-forest-900 hover:underline"
      >
        {entry.project_name}
      </Link>
    )
  }
  // The project is gone; its name (when saved) is still shown, but there is nothing to link to.
  return <span className="text-stone-500">{entry.project_name ? `${entry.project_name} (deleted)` : 'Deleted project'}</span>
}

function ActivityItem({ entry, now, showProject }: { entry: ActivityEntry; now: number; showProject: boolean }) {
  const { icon: Icon, style } = ACTION_ICONS[entry.action]
  const isAboutProject = entry.entity_type !== 'user'
  return (
    <li className="flex gap-3 py-3 first:pt-0 last:pb-0">
      <span className={`flex size-9 shrink-0 items-center justify-center rounded-full ${style}`}>
        <Icon aria-hidden className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm break-words text-stone-900">{entry.summary}</p>
        <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-stone-500">
          <time dateTime={entry.created_at} title={formatTimestamp(entry.created_at)}>
            {formatRelativeTime(entry.created_at, now)}
          </time>
          {showProject && isAboutProject && (
            <>
              <span aria-hidden>·</span>
              <ProjectReference entry={entry} />
            </>
          )}
        </p>
      </div>
    </li>
  )
}

export default function ActivityFeed({ entries, showProject }: { entries: ActivityEntry[]; showProject: boolean }) {
  const now = useNow(RELATIVE_TIME_REFRESH_MS)
  return (
    <ol aria-label="Activity, newest first" className="divide-y divide-stone-100">
      {entries.map((entry) => (
        <ActivityItem key={entry.id} entry={entry} now={now} showProject={showProject} />
      ))}
    </ol>
  )
}
