import { useEffect } from 'react'

const APP_NAME = 'VanaTrack'

/** Set the browser tab title to "<page> · VanaTrack" while this page is shown. */
export function useDocumentTitle(pageTitle: string | null): void {
  useEffect(() => {
    document.title = pageTitle ? `${pageTitle} · ${APP_NAME}` : APP_NAME
  }, [pageTitle])
}
