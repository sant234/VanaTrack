import { FileQuestion } from 'lucide-react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../../components/StatePanels'

export default function ProjectNotFound() {
  return (
    <EmptyState
      icon={FileQuestion}
      title="Project not found"
      description="It may have been deleted, or the link is wrong."
      action={
        <Link to="/projects" className="inline-flex min-h-10 items-center text-sm font-semibold text-forest-700 hover:underline">
          Back to projects
        </Link>
      }
    />
  )
}
