import React, { useState, useEffect } from 'react'
import { ArrowLeft, ZoomIn, ZoomOut, ChevronLeft, ChevronRight, Activity, AlertTriangle, CheckCircle, ShieldAlert, BarChart3, Database } from 'lucide-react'
import EegCanvasViewer from '../features/viewer/EegCanvasViewer'
import ArtifactTimeline from '../features/viewer/ArtifactTimeline'

interface SessionViewerProps {
  sessionId: string
  onBack: () => void
}

const SessionViewer: React.FC<SessionViewerProps> = ({ sessionId, onBack }) => {
  const [analysisData, setAnalysisData] = useState<any>(null)
  const [timelineData, setTimelineData] = useState<any>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  
  // UI Controls State
  const [startTime, setStartTime] = useState<number>(0)
  const [duration] = useState<number>(10) // Fixed to 10s pages for MVP Phase
  const [scaleFactor, setScaleFactor] = useState<number>(1.5) // Adjust amplitude
  
  // DSP State
  const [applyNotch, setApplyNotch] = useState<boolean>(false)
  const [applyBandpass, setApplyBandpass] = useState<boolean>(false)
  const [isSavingBaseline, setIsSavingBaseline] = useState<boolean>(false)
  const [isSavingArtifact, setIsSavingArtifact] = useState<boolean>(false)
  const [selectedArtifactLabel, setSelectedArtifactLabel] = useState<string>("blink")

  const ARTIFACT_LABELS = [
    { value: 'blink', label: 'Blink / Ocular' },
    { value: 'horizontal_eye_movement', label: 'Eye Move (Horiz)' },
    { value: 'vertical_eye_movement', label: 'Eye Move (Vert)' },
    { value: 'jaw_clench', label: 'Jaw Clench' },
    { value: 'head_movement', label: 'Head Movement' },
    { value: 'muscle_tension', label: 'Muscle / EMG' },
    { value: 'motion', label: 'Gross Motion' }
  ]

  const handleSaveBaseline = async () => {
    if (!analysisData?.features) return

    // UX Safety Warning: Check if current segment has warnings
    const hasWarnings = analysisData.quality?.warnings?.length > 0
    if (hasWarnings) {
      const confirmSave = window.confirm("⚠️ This segment contains quality warnings or artifacts. Using it as a baseline may bias future analysis. Use as baseline anyway?")
      if (!confirmSave) return
    } else {
       const confirmSave = window.confirm("Use current 10s segment (Spectral Profile) as the User Baseline for this subject?")
       if (!confirmSave) return
    }

    setIsSavingBaseline(true)
    try {
      const metadata = {
        label: "Manual Baseline",
        timestamp: new Date().toISOString(),
        data_sfreq: analysisData?.window?.sample_rate || 0
      }

      const res = await fetch('http://localhost:8000/api/v1/baselines/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          baseline_type: 'resting',
          features: analysisData.features,
          metadata: metadata
        })
      })

      if (!res.ok) throw new Error("Failed to save baseline")
      
      // Refresh to show updated comparison
      await fetchSegment(startTime)
      alert("Baseline calibrated successfully!")
    } catch (err: any) {
      alert("Error: " + err.message)
    } finally {
      setIsSavingBaseline(false)
    }
  }

  const handleSaveArtifact = async () => {
    if (!analysisData?.features) return
    
    setIsSavingArtifact(true)
    try {
      const res = await fetch('http://localhost:8000/api/v1/artifacts/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          artifact_label: selectedArtifactLabel,
          features: analysisData.features,
          metadata: {
            session_id: sessionId,
            timestamp: new Date().toISOString(),
            sfreq: analysisData?.window?.sample_rate || 0
          }
        })
      })

      if (!res.ok) throw new Error("Failed to store artifact template")
      
      alert(`Stored as ${selectedArtifactLabel} reference!`)
    } catch (err: any) {
      alert("Error: " + err.message)
    } finally {
      setIsSavingArtifact(false)
    }
  }

  const fetchTimeline = async () => {
    try {
      // Fetch the global timeline map asynchronously (don't block the viewer)
      const res = await fetch(`http://localhost:8000/api/v1/sessions/${sessionId}/timeline?window=${duration}&step=${duration}&apply_notch=${applyNotch}&apply_bandpass=${applyBandpass}`)
      if (res.ok) {
        setTimelineData(await res.json())
      }
    } catch (err) {
      console.error("Failed to load timeline", err)
    }
  }
  
  const fetchSegment = async (start: number, overrideNotch?: boolean, overrideBandpass?: boolean) => {
    setLoading(true)
    setError(null)
    
    const notch = overrideNotch !== undefined ? overrideNotch : applyNotch
    const bandpass = overrideBandpass !== undefined ? overrideBandpass : applyBandpass

    try {
      const res = await fetch(`http://localhost:8000/api/v1/sessions/${sessionId}/analysis?start=${start}&duration=${duration}&apply_notch=${notch}&apply_bandpass=${bandpass}`)
      
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to load analysis')
      }
      
      const sessionSlice = await res.json()
      setAnalysisData(sessionSlice)
      setStartTime(start)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSegment(0)
    fetchTimeline()
  }, [sessionId])

  const handleToggleNotch = () => {
    const nextVal = !applyNotch
    setApplyNotch(nextVal)
    fetchSegment(startTime, nextVal, applyBandpass)
  }

  const handleToggleBandpass = () => {
    const nextVal = !applyBandpass
    setApplyBandpass(nextVal)
    fetchSegment(startTime, applyNotch, nextVal)
  }

  const w = analysisData?.window
  const q = analysisData?.quality
  const f = analysisData?.features
  const b = analysisData?.baseline_comparison

  return (
    <div className="flex flex-col h-screen w-full bg-background text-foreground dark">
      {/* Top Navigation Bar */}
      <header className="flex items-center justify-between border-b border-border px-6 py-4 bg-card">
        <div className="flex items-center gap-4">
          <button 
            onClick={onBack}
            className="p-2 hover:bg-muted rounded-full transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <Activity className="text-primary w-6 h-6" />
            <h1 className="font-semibold text-lg">NeuroVynx Analytics</h1>
            <span className="text-xs text-muted-foreground ml-2 px-2 py-1 bg-muted rounded">
              ID: {sessionId.split('-')[0]}
            </span>
          </div>
        </div>

        {/* Toolbar Controls */}
        <div className="flex items-center gap-6">
          {/* DSP Toggles */}
          <div className="flex items-center gap-3 text-sm">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="rounded bg-input border-border" checked={applyNotch} onChange={handleToggleNotch} />
              <span>Notch (50Hz)</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="rounded bg-input border-border" checked={applyBandpass} onChange={handleToggleBandpass} />
              <span>Bandpass (1-45Hz)</span>
            </label>
          </div>
          
          <div className="h-6 w-px bg-border mx-2"></div>

          {/* Vertical Amplitude Scale */}
          <div className="flex items-center bg-muted rounded-md p-1">
            <button 
              onClick={() => setScaleFactor(prev => Math.max(0.1, prev - 0.5))}
              className="p-1.5 hover:bg-background rounded text-muted-foreground hover:text-foreground"
              title="Decrease Amplitude"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-xs px-3 font-mono w-[60px] text-center">
              x{scaleFactor.toFixed(1)}
            </span>
            <button 
              onClick={() => setScaleFactor(prev => prev + 0.5)}
              className="p-1.5 hover:bg-background rounded text-muted-foreground hover:text-foreground"
              title="Increase Amplitude"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden flex flex-col p-4 gap-4">
        
        {/* Playback & Time Controls */}
        <div className="flex items-center justify-center gap-4 py-2 shrink-0">
          <button 
            onClick={() => fetchSegment(Math.max(0, startTime - duration))}
            disabled={startTime === 0 || loading}
            className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 text-secondary-foreground rounded disabled:opacity-50"
          >
            <ChevronLeft className="w-4 h-4" /> Previous 10s
          </button>
          <span className="font-mono text-sm px-4 py-2 bg-muted rounded text-center w-[180px]">
            {startTime.toFixed(1)}s - {(startTime + duration).toFixed(1)}s
          </span>
          <button 
            onClick={() => fetchSegment(startTime + duration)}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 text-secondary-foreground rounded disabled:opacity-50"
          >
           Next 10s <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Viewer and Analytical Panels Layout */}
        <div className="flex-1 flex gap-4 min-h-0">
          
          {/* Main Waveform Signal Viewer */}
          <div className="flex-1 border border-border rounded shadow-inner overflow-hidden relative">
            {loading && !analysisData && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10 backdrop-blur-sm">
                <span className="animate-pulse font-mono">Analyzing segment...</span>
              </div>
            )}
            
            {error && (
              <div className="absolute inset-0 flex items-center justify-center bg-background z-10">
                <div className="p-4 bg-destructive/10 text-destructive border border-destructive rounded max-w-md text-center">
                  <p className="font-bold mb-2">Error loading segment</p>
                  <p className="text-sm">{error}</p>
                  <button onClick={() => fetchSegment(startTime)} className="mt-4 px-4 py-2 bg-background border border-border rounded text-foreground text-sm hover:bg-muted">Retry</button>
                </div>
              </div>
            )}

            {w && (
               <EegCanvasViewer 
                 data={w.data}
                 channels={w.channels}
                 sampleRate={w.sample_rate}
                 verticalScaleFactor={scaleFactor}
                 qualityData={q?.per_channel_status}
               />
            )}
          </div>

          {/* Right Analytical Panel Sidebar */}
          <div className="w-80 flex flex-col gap-4 overflow-hidden shrink-0">
            
            {/* Features & Baseline Module */}
            <div className="flex-1 bg-card border border-border rounded flex flex-col overflow-hidden min-h-[300px]">
              <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-primary" />
                <span className="font-semibold text-sm">Spectral Features</span>
              </div>
              <div className="flex-1 overflow-y-auto px-4 space-y-4">
                {!f ? (
                   <span className="text-xs text-muted-foreground animate-pulse">Calculating...</span>
                ) : (
                  <>
                    <h3 className="text-xs font-semibold text-muted-foreground sticky top-0 bg-card z-20 py-3 mb-2 border-b border-border/10 -mx-4 px-4">Global Band Power (Relative)</h3>
                    <div className="space-y-2">
                      {['delta', 'theta', 'alpha', 'beta'].map(band => {
                        const val = f.global_summary[`mean_relative_${band}`]
                        return (
                          <div key={band} className="flex justify-between items-center text-sm">
                            <span className="capitalize">{band}</span>
                            <div className="w-32 h-2 bg-muted rounded overflow-hidden">
                              <div className="h-full bg-primary" style={{ width: `${Math.min(val * 100, 100)}%` }}></div>
                            </div>
                            <span className="font-mono text-xs w-10 text-right">{(val * 100).toFixed(1)}%</span>
                          </div>
                        )
                      })}
                    </div>

                    <div className="pt-2 mt-4 border-t border-border">
                      <h3 className="text-xs font-semibold text-muted-foreground mb-3 flex items-center gap-2">
                        <Database className="w-3 h-3" /> Baseline Comparison
                      </h3>
                      {b?.error ? (
                        <div className="space-y-4">
                          <div className="text-xs p-2 bg-muted/50 rounded text-muted-foreground italic">
                            No baseline found for this subject. Calibrate to enable deviation analysis.
                          </div>
                          <button 
                            onClick={handleSaveBaseline}
                            disabled={isSavingBaseline || loading}
                            className="w-full text-xs py-2 bg-primary/10 border border-primary/20 text-primary rounded hover:bg-primary/20 transition-colors flex items-center justify-center gap-2"
                          >
                            <Database className="w-3 h-3" />
                            {isSavingBaseline ? 'Saving...' : 'Set Current as Baseline'}
                          </button>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Live Deviations</span>
                            <button 
                               onClick={handleSaveBaseline}
                               className="text-[10px] text-primary hover:underline hover:text-primary/80 transition-colors"
                               disabled={isSavingBaseline || loading}
                            >
                               Update Baseline
                            </button>
                          </div>

                          {/* Confidence Meter */}
                          {b?.artifact_data && (
                            <div className="p-2 bg-muted/20 border border-border/50 rounded space-y-2">
                               <div className="flex justify-between items-center text-[10px] font-bold">
                                  <span className="text-muted-foreground uppercase text-[9px] tracking-widest">Comparison Confidence</span>
                                  <span className={b.artifact_data.comparison_confidence > 0.7 ? 'text-green-500' : 'text-yellow-500'}>
                                    {(b.artifact_data.comparison_confidence * 100).toFixed(0)}%
                                  </span>
                               </div>
                               <div className="w-full h-1 bg-muted rounded-full overflow-hidden">
                                  <div 
                                    className={`h-full transition-all duration-500 ${
                                      b.artifact_data.comparison_confidence > 0.7 ? 'bg-green-500' : 
                                      b.artifact_data.comparison_confidence > 0.4 ? 'bg-yellow-500' : 'bg-destructive'
                                    }`}
                                    style={{ width: `${b.artifact_data.comparison_confidence * 100}%` }}
                                  ></div>
                               </div>
                               {b.artifact_data.match_score > 0.6 && (
                                 <div className="flex items-center gap-1.5 text-[10px] text-primary font-medium animate-pulse">
                                    <ShieldAlert className="w-3 h-3" />
                                    <span>{b.artifact_data.best_match.replace('_', ' ').toUpperCase()} Likely</span>
                                 </div>
                               )}
                            </div>
                          )}

                          <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                            {b?.interpretation?.map((interp: string, idx: number) => (
                              <div key={idx} className="text-[11px] p-2 bg-muted/30 rounded border border-border/50 leading-relaxed">
                                {interp}
                              </div>
                            ))}
                          </div>

                          {/* Artifact Calibration Library Controls */}
                          <div className="pt-3 mt-2 border-t border-border/50">
                             <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-2">Artifact Library Calibration</div>
                             <div className="flex gap-2">
                                <select 
                                  value={selectedArtifactLabel}
                                  onChange={(e) => setSelectedArtifactLabel(e.target.value)}
                                  className="flex-1 bg-muted text-[10px] border border-border rounded px-2 h-8"
                                >
                                  {ARTIFACT_LABELS.map(opt => (
                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                  ))}
                                </select>
                                <button
                                  onClick={handleSaveArtifact}
                                  disabled={isSavingArtifact || loading}
                                  className="px-3 bg-secondary text-secondary-foreground text-[10px] font-medium rounded hover:bg-secondary/80 h-8 transition-colors shrink-0"
                                >
                                  {isSavingArtifact ? '...' : 'Store'}
                                </button>
                             </div>
                             <p className="text-[9px] text-muted-foreground mt-2 leading-tight">
                                Calibrate for this subject to improve detection accuracy.
                             </p>
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Quality Summary Panel (Moved below features) */}
            <div className="flex-1 bg-card border border-border rounded flex flex-col overflow-hidden max-h-[300px]">
              <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between shrink-0">
                <span className="font-semibold text-sm">Quality Engine</span>
                {q && (
                  <span className={`text-xs px-2 py-1 rounded font-bold shadow-sm ${
                    q.overall_quality_score > 80 ? 'bg-green-500/20 text-green-500' :
                    q.overall_quality_score > 50 ? 'bg-yellow-500/20 text-yellow-500' :
                    'bg-red-500/20 text-red-500 border border-red-500/50'
                  }`}>
                    {q.overall_quality_score}%
                  </span>
                )}
              </div>
              
              <div className="flex-1 overflow-y-auto px-4">
                {!q ? (
                  <div className="text-sm text-muted-foreground p-4 animate-pulse">Running quality scan...</div>
                ) : (
                  <div className="space-y-3 pt-2">
                    {q.warnings.length > 0 && (
                      <div className="mb-4">
                        <div className="text-xs font-semibold text-destructive flex items-center gap-1 mb-2">
                          <ShieldAlert className="w-3 h-3" /> Segment Warnings
                        </div>
                        <div className="text-xs space-y-1">
                          {q.warnings.map((warn: string, i: number) => (
                            <div key={i} className="bg-destructive/10 p-1.5 rounded text-destructive leading-tight border border-destructive/20">{warn}</div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="text-xs font-semibold text-muted-foreground mb-2 sticky top-0 bg-card py-3 z-20 border-b border-border/10 -mx-4 px-4">Channel Status</div>
                    {Object.entries(q.per_channel_status).map(([ch, info]: [string, any]) => (
                      <div key={ch} className="flex items-center justify-between py-1 border-b border-border/30 last:border-0">
                        <span className="text-sm font-mono">{ch}</span>
                        {info.status === 'good' && <CheckCircle className="w-4 h-4 text-green-500" />}
                        {info.status === 'warning' && <AlertTriangle className="w-4 h-4 text-yellow-500" />}
                        {info.status === 'bad' && <ShieldAlert className="w-4 h-4 text-destructive" />}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>

        {/* Global Timeline Minimap */}
        <div className="shrink-0 w-full mt-2">
          {timelineData ? (
             <ArtifactTimeline 
               segments={timelineData.segments}
               totalDuration={timelineData.session_duration}
               viewportStart={startTime}
               viewportDuration={duration}
               onJumpTo={(target: number) => fetchSegment(target)}
             />
          ) : (
             <div className="h-12 w-full bg-muted/20 border border-border rounded flex items-center justify-center text-xs text-muted-foreground animate-pulse">
               Scanning session timeline...
             </div>
          )}
        </div>

      </div>
    </div>
  )
}

export default SessionViewer
