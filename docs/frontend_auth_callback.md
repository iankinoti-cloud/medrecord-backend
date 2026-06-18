# Frontend `/auth/callback` handler (example)

This example assumes a single-page app (React) served at `FRONTEND_URL`.

React (hook) example — reads `token` from query, stores in `localStorage`, then redirects:

```jsx
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function AuthCallback() {
  const navigate = useNavigate()

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    if (token) {
      // store securely for your app (example uses localStorage)
      localStorage.setItem('access_token', token)
      // redirect to app root or dashboard
      navigate('/', { replace: true })
    } else {
      // handle error (no token)
      navigate('/login', { replace: true })
    }
  }, [navigate])

  return <div>Signing you in…</div>
}
```

Notes:
- Use `Authorization: Bearer <token>` header for subsequent API calls.
- For improved security, consider using an HttpOnly cookie set by the backend instead of localStorage.
- Ensure the frontend URL in `.env` matches where this callback is hosted.
