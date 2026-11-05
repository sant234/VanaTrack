/**
 * "Export CSV": downloads exactly what the list shows (same filters and sort). Every role may export.
 * The file is fetched with the login token (see apiDownload); success and failure both show a toast.
 */
import { useMutation } from '@tanstack/react-query'
import { Download } from 'lucide-react'

import Button from '../../components/Button'
import { errorMessageOf, useToast } from '../../components/toast/useToast'
import { downloadProjectsCsv } from './projectsApi'
import type { ProjectListParams } from './types'

export default function ExportCsvButton({ params }: { params: ProjectListParams }) {
  const { showToast } = useToast()
  const download = useMutation({
    mutationFn: () => downloadProjectsCsv(params),
    onSuccess: () => showToast('success', 'The CSV file was downloaded.'),
    onError: (error) => showToast('error', errorMessageOf(error, 'Could not export the projects.')),
  })
  return (
    <Button variant="secondary" onClick={() => download.mutate()} isLoading={download.isPending}>
      {!download.isPending && <Download aria-hidden className="size-4" />}
      Export CSV
    </Button>
  )
}
