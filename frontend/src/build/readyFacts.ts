import type { ProjectResponse } from '../api/client'

// "9 files · 14 KB · 5 of 5 tests passed". Pieces the server did not send are left out, never shown as "null".
export function factsLine(project: ProjectResponse): string {
  const pieces: string[] = []
  if (project.file_count != null) {
    pieces.push(
      `${project.file_count} ${project.file_count === 1 ? 'file' : 'files'}`,
    )
  }
  if (project.size_kb != null) pieces.push(`${project.size_kb} KB`)
  // "0 of 0 tests passed" says nothing (no test output came back), so it is left out.
  if (
    project.tests_passed != null &&
    project.tests_total != null &&
    project.tests_total > 0
  ) {
    pieces.push(
      `${project.tests_passed} of ${project.tests_total} tests passed`,
    )
  }
  return pieces.join(' · ')
}
