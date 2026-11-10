// LOCAL ONLY. Who is logged in, and the log in / sign up / log out actions.
import { useEffect, useState } from 'react'
import {
  getToken,
  logIn,
  logOut,
  setLoggedOutHandler,
  setToken,
  signUp,
  whoAmI,
  type User,
} from './api'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  // True while we check a token saved from before a page refresh
  const [checking, setChecking] = useState<boolean>(getToken() !== null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // If any request finds the login has ended, show the login card again
    setLoggedOutHandler(() => setUser(null))
    if (getToken() === null) return
    whoAmI()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setChecking(false))
  }, [])

  async function run(action: () => Promise<User>) {
    if (busy) return // a double-click sends once
    setBusy(true)
    setError(null)
    try {
      setUser(await action())
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : 'Something went wrong.',
      )
    } finally {
      setBusy(false)
    }
  }

  return {
    user,
    checking,
    busy,
    error,
    logIn: (email: string, password: string) =>
      run(() => logIn(email, password)),
    signUp: (email: string, password: string) =>
      run(() => signUp(email, password)),
    logOut: async () => {
      await logOut()
      setUser(null)
    },
  }
}
