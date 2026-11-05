import { useNavigate } from 'react-router-dom'

import Skeleton from '../../components/Skeleton'
import { ErrorState } from '../../components/StatePanels'
import { useToast } from '../../components/toast/useToast'
import { ApiError } from '../../lib/api'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import NotAuthorizedPage from '../../pages/NotAuthorizedPage'
import ProjectForm from './ProjectForm'
import ProjectNotFound from './ProjectNotFound'
import { formValuesFromProject } from './projectFormValues'
import { useProject, useProjectOptions, useUpdateProject } from './useProjects'
import { useProjectIdParam } from './useProjectIdParam'

const NOT_FOUND_STATUS = 404

export default function EditProjectPage() {
  const projectId = useProjectIdParam()
  const navigate = useNavigate()
  const project = useProject(projectId)
  const options = useProjectOptions()
  const updateProject = useUpdateProject(projectId)
  const { showToast } = useToast()

  const isMissing =
    Number.isNaN(projectId) || (project.error instanceof ApiError && project.error.status === NOT_FOUND_STATUS)
  // The backend would refuse the save anyway (403); this just avoids showing a form that cannot work.
  const isForbidden = project.data !== undefined && !project.data.can_edit
  useDocumentTitle(isMissing ? 'Project not found' : isForbidden ? 'Not authorized' : 'Edit project')

  if (isForbidden) return <NotAuthorizedPage />

  function renderBody() {
    if (isMissing) return <ProjectNotFound />
    if (project.isError) return <ErrorState message={project.error.message} onRetry={() => void project.refetch()} />
    if (options.isError) return <ErrorState message={options.error.message} onRetry={() => void options.refetch()} />
    if (!project.data || !options.data) return <Skeleton className="h-96" />

    return (
      <ProjectForm
        key={project.data.id}
        initialValues={formValuesFromProject(project.data)}
        options={options.data}
        currentValue={project.data.current_value}
        submitLabel="Save changes"
        cancelTo={`/projects/${projectId}`}
        onSubmit={async (input) => {
          const saved = await updateProject.mutateAsync(input)
          showToast('success', `Changes to “${saved.name}” were saved.`)
          navigate(`/projects/${projectId}`, { replace: true })
        }}
      />
    )
  }

  return (
    <section className="mx-auto max-w-3xl space-y-5">
      <h1 className="text-2xl font-bold text-stone-900">Edit project</h1>
      {renderBody()}
    </section>
  )
}
