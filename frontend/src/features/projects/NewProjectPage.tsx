import { useNavigate } from 'react-router-dom'

import { useToast } from '../../components/toast/useToast'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import Skeleton from '../../components/Skeleton'
import { ErrorState } from '../../components/StatePanels'
import ProjectForm from './ProjectForm'
import { EMPTY_PROJECT_FORM } from './projectFormValues'
import { useCreateProject, useProjectOptions } from './useProjects'

export default function NewProjectPage() {
  useDocumentTitle('New project')
  const navigate = useNavigate()
  const options = useProjectOptions()
  const createProject = useCreateProject()
  const { showToast } = useToast()

  return (
    <section className="mx-auto max-w-3xl space-y-5">
      <h1 className="text-2xl font-bold text-stone-900">New project</h1>
      {options.isPending && <Skeleton className="h-96" />}
      {options.isError && <ErrorState message={options.error.message} onRetry={() => void options.refetch()} />}
      {options.data && (
        <ProjectForm
          initialValues={EMPTY_PROJECT_FORM}
          options={options.data}
          submitLabel="Create project"
          cancelTo="/projects"
          onSubmit={async (input) => {
            const project = await createProject.mutateAsync(input)
            showToast('success', `Project “${project.name}” was created.`)
            navigate(`/projects/${project.id}`, { replace: true })
          }}
        />
      )}
    </section>
  )
}
