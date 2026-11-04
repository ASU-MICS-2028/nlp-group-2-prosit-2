import { Button } from './Button'
import { Notice } from './Notice'

type Props = {
  // refused: we will not build this (for example, it could harm someone)
  // unsupported: we cannot build this yet
  reason: 'refused' | 'unsupported'
  message: string
  // Optional suggestion for something close that we can build
  alternative?: string
  onStartOver: () => void
}

// Shown instead of questions or a plan when the request cannot go ahead.
export function CannotBuildNotice({
  reason,
  message,
  alternative,
  onStartOver,
}: Props) {
  const refused = reason === 'refused'
  return (
    <Notice
      tone={refused ? 'error' : 'info'}
      title={
        refused
          ? 'We cannot build that'
          : 'That is not something we can build yet'
      }
      action={<Button onClick={onStartOver}>Change my request</Button>}
    >
      {message}
      {alternative && <> {alternative}</>}
    </Notice>
  )
}
