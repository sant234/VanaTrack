/**
 * "Export CSV": downloads exactly what the list shows (same filters and sort). Every role may export.
 * The file is fetched with the login token (see apiDownload), so a failed download shows a message here.
 */
import { useMutation } from '@tanstack/react-query'
import { Download } from 'lucide-react'

import Alert from '../../components/Alert'
import Button from '../../components/Button'
import { ApiError } from '../../lib/api'
import { downloadProjectsCsv } from './projectsApi'
import type { ProjectListParams } from './types'

export default function ExportCsvButton({ params }: { params: ProjectListParams }) {
  const download = useMutation({ mutationFn: () => downloadProjectsCsv(params) })
  return (
    <div className="flex flex-col items-end gap-2">
      <Button variant="secondary" onClick={() => download.mutate()} isLoading={download.isPending}>
        {!download.isPending && <Download aria-hidden className="size-4" />}
        Export CSV
      </Button>
      {download.isError && (
        <Alert>
          {download.error instanceof ApiError ? download.error.message : 'Could not export the projects.'}
        </Alert>
      )}
    </div>
  )
}
