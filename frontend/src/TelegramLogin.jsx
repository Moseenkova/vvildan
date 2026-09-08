import { useEffect, useRef, useState } from 'react'
import api from './api'

export default function TelegramLogin({ onLogin, registrationMessage }) {
  const container = useRef(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [botUsername, setBotUsername] = useState('')

  useEffect(() => {
    let cancelled = false
    const target = container.current
    window.onTelegramBrowserLogin = async (user) => {
      setBusy(true)
      setError('')
      try {
        const { data } = await api.post('/api/auth/telegram', user)
        if (!cancelled) onLogin(data.access_token)
      } catch (error) {
        if (!cancelled) setError(error.response?.status === 404
          ? registrationMessage : 'Telegram login failed. Please try again.')
      } finally {
        if (!cancelled) setBusy(false)
      }
    }
    api.get('/api/auth/telegram/config').then(({ data }) => {
      if (cancelled) return
      setBotUsername(data.bot_username)
      const script = document.createElement('script')
      script.src = 'https://telegram.org/js/telegram-widget.js?22'
      script.async = true
      script.setAttribute('data-telegram-login', data.bot_username)
      script.setAttribute('data-size', 'large')
      script.setAttribute('data-onauth', 'onTelegramBrowserLogin(user)')
      script.onerror = () => setError('Unable to load Telegram login. Please try again.')
      target.replaceChildren(script)
    }).catch(() => {
      if (!cancelled) setError('Unable to load Telegram login. Please try again.')
    })
    return () => {
      cancelled = true
      delete window.onTelegramBrowserLogin
      target.replaceChildren()
    }
  }, [onLogin, registrationMessage, attempt])

  return (
    <main className="app-container not-found">
      <h1>Log in with Telegram</h1>
      <p>Sign in to create and manage your requests.</p>
      <div ref={container} />
      {busy && <p role="status">Signing in…</p>}
      {error && <><p role="alert">{error}</p><button type="button" onClick={() => { setError(''); setAttempt(attempt + 1) }}>Try again</button></>}
      {botUsername && <p><a href={`https://t.me/${botUsername}`} target="_blank" rel="noreferrer">Open Telegram bot to register</a></p>}
    </main>
  )
}
