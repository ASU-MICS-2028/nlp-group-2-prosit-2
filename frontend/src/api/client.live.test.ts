// @vitest-environment node
//
// Live tests: these call a REAL backend. Nothing is faked.
// They only run when VITE_LIVE_API=1 is set, so CI (which has no backend for the frontend job) skips them.
//
// How to run:
//   1. Terminal 1 (repo root):  source backend/.venv/bin/activate && uvicorn backend.main:app
//   2. Terminal 2 (frontend/):  VITE_LIVE_API=1 npm test -- --run client.live
//      (Windows PowerShell:     $env:VITE_LIVE_API=1; npm test -- --run client.live)

import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError,
  eventsUrl,
  getHealth,
  getProject,
  listProjects,
  startProject,
} from './client'

// Runs the call and returns the ApiError it threw, so a test can check the message.
async function failureOf(call: Promise<unknown>): Promise<ApiError> {
  try {
    await call
  } catch (error) {
    if (error instanceof ApiError) return error
    throw error
  }
  throw new Error('The call was expected to fail, but it succeeded.')
}

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

describe.skipIf(!import.meta.env.VITE_LIVE_API)(
  'against a real backend',
  () => {
    it('getHealth says the server is ok', async () => {
      expect(await getHealth()).toEqual({ status: 'ok' })
    })

    it('startProject creates a waiting project, and getProject finds it', async () => {
      const started = await startProject('A bookshop where I can add books')

      expect(started.id).toMatch(/^p_\d+$/)
      expect(started.status).toBe('waiting')
      expect(Array.isArray(started.questions)).toBe(true)

      const found = await getProject(started.id)
      expect(found).toEqual({ id: started.id, status: 'waiting' })
    })

    it('listProjects shows the newest project first', async () => {
      const first = await startProject('A to-do list API')
      const second = await startProject('A clinic appointments API')

      const listed = await listProjects()

      const ids = listed.map((project) => project.id)
      expect(ids.indexOf(second.id)).toBeLessThan(ids.indexOf(first.id))
      expect(Object.keys(listed[0]).sort()).toEqual([
        'id',
        'name',
        'status',
        'updated_at',
      ])
    })

    it('an empty request is refused with a plain sentence (422)', async () => {
      const error = await failureOf(startProject('   '))

      expect(error.status).toBe(422)
      expect(error.message).not.toBe('')
      expect(error.message).not.toContain('[') // not FastAPI's technical list
    })

    it('a request over 2000 characters is refused (422)', async () => {
      const error = await failureOf(startProject('a'.repeat(2001)))

      expect(error.status).toBe(422)
    })

    it('an unknown project gives the 404 sentence', async () => {
      const error = await failureOf(getProject('p_does_not_exist'))

      expect(error.status).toBe(404)
      expect(error.message).toBe('Project not found.')
    })

    it('an odd id cannot reach another address', async () => {
      // "../health" would reach /health if it were not escaped. Escaped, it is just an unknown project.
      const error = await failureOf(getProject('../health'))

      expect(error.status).toBe(404)
    })

    it('the events address really streams the first event', async () => {
      const started = await startProject('A recipe book API')
      const controller = new AbortController()

      const response = await fetch(eventsUrl(started.id), {
        signal: controller.signal,
      })
      const reader = response.body!.getReader()
      const { value } = await reader.read() // wait for the first chunk
      controller.abort() // hang up: the stream of a waiting project never ends on its own

      expect(response.status).toBe(200)
      expect(new TextDecoder().decode(value)).toContain('"status":"waiting"')
    })

    it('says we could not reach the server when nothing is listening', async () => {
      // Port 1 has nothing listening, so the connection is really refused. No fake involved.
      vi.stubEnv('VITE_API_URL', 'http://localhost:1')
      vi.resetModules()
      const offline = await import('./client')

      // We re-imported the client, so its ApiError is a different copy from ours: check its name, not instanceof.
      const error = await offline.getHealth().then(
        () => null,
        (caught: unknown) => caught,
      )

      expect(error).toMatchObject({
        name: 'ApiError',
        status: null,
        message: expect.stringContaining('could not reach the server'),
      })
    })
  },
)
