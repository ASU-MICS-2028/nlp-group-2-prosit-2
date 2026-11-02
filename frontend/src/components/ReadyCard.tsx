import { Check, Copy, Download } from 'lucide-react'
import { useState } from 'react'
import { Button } from './Button'
import { Notice } from './Notice'

type Props = {
  fileCount: number
  sizeKb: number
  testsPassed: number
  testsTotal: number
  runCommand: string
  onDownload: () => void
  downloadError?: string
}

export function ReadyCard({
  fileCount,
  sizeKb,
  testsPassed,
  testsTotal,
  runCommand,
  onDownload,
  downloadError,
}: Props) {
  const [copied, setCopied] = useState(false)

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(runCommand)
      setCopied(true)
    } catch {
      // Clipboard can be blocked by the browser; the command is still visible to select by hand
      setCopied(false)
    }
  }

  return (
    <div className="warm-card card">
      <span className="ready__check">
        <Check size={20} aria-hidden />
      </span>
      <div>
        <h2 className="t-title" style={{ margin: 0 }}>
          Your API is ready
        </h2>
        <span className="t-caption muted">
          {fileCount} files · {sizeKb} KB · {testsPassed} of {testsTotal} tests
          passed
        </span>
      </div>

      {downloadError && (
        <Notice tone="error" title="The download did not start">
          {downloadError}
        </Notice>
      )}

      <div>
        <Button variant="primary" onClick={onDownload}>
          <Download size={16} aria-hidden />
          Download project (.zip)
        </Button>
      </div>

      <div className="well ready__command">
        <code className="t-code">{runCommand}</code>
        <Button variant="ghost" onClick={copyCommand}>
          <Copy size={16} aria-hidden />
          {copied ? 'Copied' : 'Copy'}
        </Button>
      </div>
      <span className="muted">
        Then open localhost:8000/docs to try every endpoint.
      </span>
    </div>
  )
}
