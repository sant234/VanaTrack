/**
 * Dashboard colours. Checked with the data-visualisation palette validator on a white surface:
 * - single-hue bars and the trend line use forest-500 (#3f8f55): passes lightness, chroma, contrast.
 * - the three progress states below pass, with red↔green in the "allowed only with a second cue" band
 *   (ΔE 6.8 for red-green colour blindness), so every bar ALSO prints its state as text.
 */
export const SERIES_COLOR = 'bg-[#3f8f55]'
export const SERIES_HEX = '#3f8f55'

export type ProgressState = 'on_track' | 'behind' | 'exceeded'

export const PROGRESS_STATE_STYLE: Record<ProgressState, { bar: string; label: string }> = {
  on_track: { bar: 'bg-[#3f8f55]', label: 'On track' },
  behind: { bar: 'bg-[#e34948]', label: 'Behind' },
  exceeded: { bar: 'bg-[#2a78d6]', label: 'Exceeded' },
}
