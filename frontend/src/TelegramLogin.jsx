import { useEffect, useRef, useState } from 'react'
import api from './api'

let sdkPromise
function loadLoginSdk() {
  if (window.Telegram?.Login) return Promise.resolve(window.Telegram.Login)
  if (!sdkPromise) {
    sdkPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = 'https://oauth.telegram.org/js/telegram-login.js?6'
      script.async = true
      script.onload = () => {
        if (window.Telegram?.Login) resolve(window.Telegram.Login)
        else { script.remove(); reject(new Error('Telegram login did not load')) }
      }
      script.onerror = () => { script.remove(); reject(new Error('Unable to load Telegram login')) }
      document.head.appendChild(script)
    }).catch((error) => { sdkPromise = undefined; throw error })
  }
  return sdkPromise
}

export default function TelegramLogin({ onLogin, registrationMessage }) {
  const login = useRef(null)
  const [error, setError] = useState('')
  const [ready, setReady] = useState(false)
  const [busy, setBusy] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [botUsername, setBotUsername] = useState('')

  useEffect(() => {
    let cancelled = false
    Promise.all([api.get('/api/auth/telegram/config'), loadLoginSdk()]).then(([{ data }, sdk]) => {
      if (cancelled) return
      setBotUsername(data.bot_username)
      login.current = () => sdk.auth({
        client_id: data.client_id,
        scope: ['profile'],
        nonce: data.nonce,
      }, async (result) => {
        if (cancelled) return
        if (!result?.id_token) {
          setBusy(false)
          setError(result?.error === 'popup_closed'
            ? 'Login was cancelled. Please try again.' : 'Unable to open Telegram login. Please allow popups and try again.')
          return
        }
        try {
          const { data: tokens } = await api.post('/api/auth/telegram', { id_token: result.id_token })
          if (!cancelled) onLogin(tokens.access_token)
        } catch (error) {
          if (!cancelled) {
            setReady(false)
            setError(error.response?.status === 404
              ? registrationMessage : 'Telegram login failed. Please try again.')
          }
        } finally {
          if (!cancelled) setBusy(false)
        }
      })
      setReady(true)
    }).catch(() => {
      if (!cancelled) setError('Unable to load Telegram login. Please try again later.')
    })
    return () => {
      cancelled = true
      login.current = null
      window.Telegram?.Login?.close?.()
    }
  }, [onLogin, registrationMessage, attempt])

  const signIn = () => {
    setError('')
    setBusy(true)
    try { login.current() } catch {
      setBusy(false)
      setError('Unable to open Telegram login. Please try again.')
    }
  }

  return (
    <main className="app-container not-found">
      <h1>Log in with Telegram</h1>
      <p>Sign in to create and manage your requests.</p>
      <button type="button" className="role-button active" disabled={!ready || busy} onClick={signIn}>
        {busy ? 'Signing in…' : 'Log in with Telegram'}
      </button>
      {busy && <button type="button" onClick={() => {
        setReady(false); setBusy(false); setAttempt(attempt + 1)
      }}>Cancel</button>}
      {!ready && !error && <p role="status">Loading Telegram login…</p>}
      {error && <><p role="alert">{error}</p><button type="button" onClick={() => {
        setError(''); setReady(false); setBusy(false); setAttempt(attempt + 1)
      }}>Try again</button></>}
      {botUsername && <p><a href={`https://t.me/${botUsername}`} target="_blank" rel="noreferrer">Open Telegram bot to register</a></p>}
    </main>
  )
}
