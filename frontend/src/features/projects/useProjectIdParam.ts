import { useParams } from 'react-router-dom'

/** The numeric :projectId from the URL, or NaN if the URL holds something else (e.g. /projects/abc). */
export function useProjectIdParam(): number {
  const { projectId } = useParams()
  return /^\d+$/.test(projectId ?? '') ? Number(projectId) : Number.NaN
}
