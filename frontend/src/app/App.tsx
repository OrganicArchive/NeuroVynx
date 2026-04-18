import { useState, useEffect } from 'react'
import { Activity, Upload, Monitor } from 'lucide-react'
import SessionViewer from './SessionViewer'
import PluginManager from '../features/plugins/PluginManager'
import { Settings as SettingsIcon } from 'lucide-react'

function App() {
  const [apiStatus, setApiStatus] = useState<string>('checking...')
  const [sessionInfo, setSessionInfo] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  
  // Basic routing state
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [showPluginManager, setShowPluginManager] = useState(false)

  // Test FastAPI connection on load with polling fallback
  useEffect(() => {
    const checkHealth = () => {
      fetch('http://localhost:8000/health')
        .then(res => res.json())
        .then(data => {
          setApiStatus(`Healthy: ${data.project}`)
        })
        .catch(_err => {
          setApiStatus('Disconnected')
          // Retry in 3 seconds if disconnected
          setTimeout(checkHealth, 3000)
        })
    }
    
    checkHealth()
  }, [])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return
    
    setError(null)
    const file = e.target.files[0]
    
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://localhost:8000/api/v1/eeg/upload', {
        method: 'POST',
        body: formData,
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed')
      }
      
      setSessionInfo(data)
    } catch (err: any) {
      setError(err.message)
    }
  }

  // If we have an active session, render the viewer
  if (activeSessionId) {
    return <SessionViewer sessionId={activeSessionId} onBack={() => setActiveSessionId(null)} />
  }

  if (showPluginManager) {
    return <PluginManager onBack={() => setShowPluginManager(false)} />
  }

  return (
    <div className="min-h-screen bg-background text-foreground p-8 flex flex-col items-center">
      <header className="w-full max-w-4xl flex justify-between items-center mb-12">
        <div className="flex items-center gap-2">
          <Activity className="text-primary w-8 h-8" />
          <h1 className="text-2xl font-bold tracking-tight">NeuroVynx EEG Analytics</h1>
        </div>
        
        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground mr-2">Backend API:</span>
            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${apiStatus.includes('Healthy') ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
              {apiStatus}
            </span>
          </div>
          <button 
            onClick={() => setShowPluginManager(true)}
            className="flex items-center gap-2 mt-2 px-3 py-1.5 rounded-md bg-secondary hover:bg-muted text-xs font-medium border border-border transition-colors shadow-sm"
          >
            <SettingsIcon size={14} />
            Manage Plugins
          </button>
          {!apiStatus.includes('Healthy') && (
            <span className="text-[10px] text-muted-foreground animate-pulse mt-1">
              Tip: Ensure the "NeuroVynx Backend" window is open
            </span>
          )}
        </div>
      </header>

      <main className="w-full max-w-4xl flex flex-col items-center justify-center p-12 border-2 border-dashed border-border rounded-xl bg-card">
        <Upload className="w-12 h-12 text-muted-foreground mb-4" />
        <h2 className="text-xl font-semibold mb-2">Initialize Session</h2>
        <p className="text-muted-foreground mb-6">Import a standard .edf or .bdf standardized file to boot the analysis engine</p>
        
        <label className="bg-primary text-primary-foreground hover:bg-primary/90 px-6 py-3 rounded-md cursor-pointer font-medium transition-colors">
          Select EEG File
          <input type="file" accept=".edf,.bdf" className="hidden" onChange={handleFileUpload} />
        </label>

        {error && (
          <div className="mt-6 p-4 bg-destructive/10 text-destructive rounded-md w-full max-w-md text-center">
            {error}
          </div>
        )}

        {sessionInfo && (
          <div className="mt-8 p-6 bg-secondary text-secondary-foreground rounded-lg w-full max-w-md">
            <h3 className="font-semibold text-lg mb-4 text-center">Session Created!</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Session ID:</span>
                <span className="font-mono text-xs">{sessionInfo.session_id.split('-')[0]}...</span>
              </div>
              <div className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted-foreground">File:</span>
                <span className="truncate max-w-[200px]">{sessionInfo.filename}</span>
              </div>
              <div className="flex justify-between pb-2">
                <span className="text-muted-foreground">Duration:</span>
                <span>{sessionInfo.duration_seconds}s</span>
              </div>
            </div>
            <button 
              onClick={() => setActiveSessionId(sessionInfo.session_id)}
              className="w-full mt-6 flex items-center justify-center gap-2 bg-background border border-input px-4 py-3 rounded-md font-semibold hover:bg-muted transition-colors shadow-sm"
            >
              <Monitor className="w-4 h-4" />
              Open Signal Viewer
            </button>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
