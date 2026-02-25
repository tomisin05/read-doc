// src/App.jsx
import { useAuth } from './hooks/useAuth'
import AuthPage from './components/AuthPage'
import Dashboard from './components/Dashboard'
import LoadingScreen from './components/LoadingScreen'

export default function App() {
  const { user, loading } = useAuth()

  if (loading) return <LoadingScreen />
  if (!user) return <AuthPage />
  return <Dashboard user={user} />
}
