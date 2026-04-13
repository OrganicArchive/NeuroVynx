import React, { useState, useEffect } from 'react'
import { ArrowLeft, ZoomIn, ZoomOut, ChevronLeft, ChevronRight, Activity, AlertTriangle, BarChart3, Database, Brain, LayoutGrid, Scale, Zap, TrendingUp, TrendingDown, Minus, Map as MapIcon } from 'lucide-react'
import EegCanvasViewer from '../features/viewer/EegCanvasViewer'
import ArtifactTimeline from '../features/viewer/ArtifactTimeline'
import BrainTopomap from '../features/qeeg/BrainTopomap'

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
  const [recordingContext, setRecordingContext] = useState<string>("awake")
  const [selectedTopoBand, setSelectedTopoBand] = useState<string>("alpha")
  
  // SUBJECT DEMOGRAPHICS (Phase 3)
  const [age, setAge] = useState<number | null>(25) 
  const [mapMode, setMapMode] = useState<'relative' | 'normative'>('relative')

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
      let url = `http://localhost:8000/api/v1/sessions/${sessionId}/analysis?start=${start}&duration=${duration}&apply_notch=${notch}&apply_bandpass=${bandpass}&context=${recordingContext}`
      if (age) url += `&age=${age}`
      
      const res = await fetch(url)
      
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
    
    fetch(`http://localhost:8000/api/v1/sessions/${sessionId}`)
      .then(res => res.json())
      .then(data => {
        if (data.recording_context) {
          setRecordingContext(data.recording_context)
        }
      })
  }, [sessionId, recordingContext])

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
  const qeeg = analysisData?.qeeg
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

        <div className="flex items-center gap-6">
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

          <div className="flex items-center gap-3 bg-secondary/30 px-3 py-1.5 rounded-md border border-border/50">
            <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Context</span>
            <select 
              value={recordingContext} 
              onChange={(e) => {
                setRecordingContext(e.target.value)
                fetchSegment(startTime, applyNotch, applyBandpass)
              }}
              className="bg-transparent text-xs font-semibold focus:outline-none cursor-pointer"
            >
              <option value="awake" className="bg-card">Awake EEG</option>
              <option value="sleep" className="bg-card">Sleep EEG</option>
            </select>
          </div>
          
          <div className="h-6 w-px bg-border mx-2"></div>

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

                          {b?.artifact_data && (
                            <div className="p-2 bg-muted/20 border border-border/50 rounded space-y-2">
                               <div className="flex justify-between items-center text-[10px] font-bold">
                                  <span className="text-muted-foreground uppercase text-[9px] tracking-widest">Confidence</span>
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
                            </div>
                          )}

                          <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                            {b?.interpretation?.map((interp: string, idx: number) => (
                              <div key={idx} className="text-[11px] p-2 bg-muted/30 rounded border border-border/50 leading-relaxed">
                                {interp}
                              </div>
                            ))}
                          </div>

                          <div className="pt-3 mt-2 border-t border-border/50">
                             <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-2 text-center">Library Calibration</div>
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
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* qEEG Quantitative Analysis Panel */}
            <div className="flex-1 bg-card border border-border rounded flex flex-col overflow-hidden">
               <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-2">
                    <Brain className="w-4 h-4 text-primary" />
                    <span className="font-semibold text-sm">Quantitative EEG (qEEG)</span>
                  </div>
                  {qeeg?.is_available && (
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                        qeeg.trust_level === 'trusted' ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 
                        qeeg.trust_level === 'borderline' ? 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20' : 
                        'bg-muted text-muted-foreground border border-border'
                      }`}>
                        {qeeg.trust_level}
                      </span>
                    </div>
                  )}
               </div>

               <div className="flex-1 overflow-y-auto p-4 space-y-6">
                  {!qeeg ? (
                    <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
                       <Zap className="w-8 h-8 opacity-20" />
                       <span className="text-xs">Initializing qEEG...</span>
                    </div>
                  ) : !qeeg.is_available ? (
                    <div className="bg-muted/30 border border-dashed border-border p-6 rounded-lg text-center">
                       <AlertTriangle className="w-6 h-6 text-yellow-500/50 mx-auto mb-3" />
                       <p className="text-xs text-muted-foreground leading-relaxed italic">
                          {qeeg.reason || "Quantitative metrics unavailable."}
                       </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {/* Temporal Dynamics (Phase 2A) */}
                      <div className="space-y-4 pt-1">
                          <div className="flex items-center justify-between px-1 border-b border-border/10 pb-2">
                             <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                <Activity className="w-3 h-3" /> Temporal Dynamics
                             </div>
                             {analysisData?.temporal_qeeg?.is_available && (
                                <div className={`text-[9px] px-1.5 py-0.5 rounded border uppercase font-bold ${
                                  analysisData?.temporal_qeeg?.summary?.overall_stability === 'high' ? 'bg-green-500/10 text-green-500 border-green-500/20' :
                                  analysisData?.temporal_qeeg?.summary?.overall_stability === 'moderate' ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' :
                                  'bg-red-500/10 text-red-500 border-red-500/20'
                                }`}>
                                  {analysisData?.temporal_qeeg?.summary?.overall_stability || 'Unstable'}
                                </div>
                             )}
                          </div>

                          {!analysisData?.temporal_qeeg?.is_available ? (
                             <div className="p-3 bg-muted/10 border border-dashed border-border/40 rounded italic text-center">
                                <p className="text-[10px] text-muted-foreground">
                                   {analysisData?.temporal_qeeg?.reason || "Tracking trends..."}
                                </p>
                             </div>
                          ) : (
                             <div className="space-y-3">
                                <div className="grid grid-cols-2 gap-2">
                                   {['delta', 'theta', 'alpha', 'beta'].map(band => {
                                      const trend = analysisData.temporal_qeeg.global_band_trends[band];
                                      if (!trend) return null;
                                      return (
                                        <div key={band} className="p-2 bg-muted/10 border border-border/40 rounded flex flex-col gap-1">
                                           <div className="flex items-center justify-between">
                                              <span className="text-[10px] uppercase font-bold text-muted-foreground">{band}</span>
                                              {trend.trend === 'rising' ? <TrendingUp className="w-2.5 h-2.5 text-red-400" /> :
                                               trend.trend === 'falling' ? <TrendingDown className="w-2.5 h-2.5 text-blue-400" /> :
                                               <Minus className="w-2.5 h-2.5 text-muted-foreground/40" />}
                                           </div>
                                           <div className="flex items-end justify-between leading-none pr-1">
                                              <span className="text-xs font-mono font-bold">{(trend.current * 100).toFixed(1)}%</span>
                                           </div>
                                        </div>
                                      )
                                   })}
                                </div>
                                <div className="text-[10px] text-muted-foreground bg-muted/5 p-2 border border-border/20 rounded-md italic text-center leading-tight">
                                   {analysisData?.temporal_qeeg?.summary?.dominant_temporal_pattern || 'Analyzing trends...'}
                                </div>
                             </div>
                          )}
                      </div>

                      {/* Spatial Topography (Phase 2B/3B) */}
                      <div className="space-y-4 pt-1">
                          <div className="flex items-center justify-between px-1 border-b border-border/10 pb-2">
                             <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                <MapIcon className="w-3 h-3" /> Scalp Topography
                             </div>
                             <div className="flex items-center gap-2">
                                <div className="flex bg-muted/20 p-0.5 rounded border border-border/20">
                                   <button 
                                     onClick={() => setMapMode('relative')}
                                     className={`text-[8px] px-1.5 py-0.5 rounded transition-all uppercase font-bold ${
                                       mapMode === 'relative' ? 'bg-background text-primary shadow-sm' : 'text-muted-foreground opacity-60'
                                     }`}
                                   >
                                      Relative
                                   </button>
                                   <button 
                                     onClick={() => setMapMode('normative')}
                                     disabled={!analysisData?.normative_topography?.is_available}
                                     className={`text-[8px] px-1.5 py-0.5 rounded transition-all uppercase font-bold disabled:opacity-20 ${
                                       mapMode === 'normative' ? 'bg-background text-primary shadow-sm' : 'text-muted-foreground opacity-60'
                                     }`}
                                   >
                                      Deviation
                                   </button>
                                </div>
                                <div className="flex gap-1">
                                   {['delta', 'theta', 'alpha', 'beta'].map(b => (
                                      <button 
                                        key={b}
                                        onClick={() => setSelectedTopoBand(b)}
                                        className={`text-[8px] px-1.5 py-0.5 rounded border transition-colors ${
                                          selectedTopoBand === b ? 'bg-primary/20 border-primary/40 text-primary font-bold' : 'bg-muted/5 border-border/20 text-muted-foreground'
                                        }`}
                                      >
                                         {b[0].toUpperCase()}
                                      </button>
                                   ))}
                                </div>
                             </div>
                          </div>

                          {!analysisData?.topography?.is_available ? (
                             <div className="p-3 bg-muted/10 border border-dashed border-border/40 rounded italic text-center">
                                <p className="text-[10px] text-muted-foreground">
                                   {analysisData?.topography?.reason || "Spatial data N/A."}
                                </p>
                             </div>
                          ) : (
                             <div className="space-y-3">
                                <div className="relative">
                                  {mapMode === 'normative' && analysisData.normative_topography?.is_available ? (
                                     <BrainTopomap 
                                        gridData={analysisData.normative_topography.bands[selectedTopoBand].surface}
                                        electrodes={analysisData.topography.electrodes}
                                        trustLevel={analysisData.normative_topography.trust_level}
                                        metricLabel={selectedTopoBand.toUpperCase()}
                                        vMin={analysisData.normative_topography.bands[selectedTopoBand].z_min}
                                        vMax={analysisData.normative_topography.bands[selectedTopoBand].z_max}
                                        isLowVariance={false}
                                        mapType="normative_z_map"
                                        symmetricLimit={analysisData.normative_topography.bands[selectedTopoBand].symmetric_limit}
                                     />
                                  ) : (
                                     <BrainTopomap 
                                        gridData={analysisData.topography.bands[selectedTopoBand].surface}
                                        electrodes={analysisData.topography.electrodes}
                                        trustLevel={analysisData.topography.trust_level}
                                        metricLabel={selectedTopoBand.toUpperCase()}
                                        vMin={analysisData.topography.bands[selectedTopoBand].v_min}
                                        vMax={analysisData.topography.bands[selectedTopoBand].v_max}
                                        isLowVariance={analysisData.topography.bands[selectedTopoBand].low_variance_mode}
                                        mapType="relative_power"
                                     />
                                  )}
                                </div>
                                
                                <div className="px-3 py-2 bg-muted/20 border border-border/30 rounded flex flex-col gap-1 text-center">
                                   <div className="text-[10px] font-bold text-primary uppercase">
                                      {mapMode === 'normative' 
                                         ? analysisData.normative_topography.summary.pattern_hint 
                                         : analysisData.topography.summary.pattern_hint
                                      }
                                   </div>
                                   <p className="text-[8px] text-muted-foreground italic leading-tight opacity-70">
                                      {mapMode === 'normative' 
                                         ? analysisData.normative_topography.summary.disclaimer 
                                         : `Dominant activity detected in ${analysisData.topography.summary.strongest_region}.`
                                      }
                                   </p>
                                </div>
                             </div>
                          )}
                      </div>

                      {/* Normative Comparison (Phase 3A) */}
                      <div className="space-y-4 pt-1">
                         <div className="flex items-center justify-between px-1 border-b border-border/10 pb-2">
                            <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                               <Database className="w-3 h-3" /> Normative Analysis
                            </div>
                            <div className="flex items-center gap-2">
                               <span className="text-[9px] text-muted-foreground font-bold">Age:</span>
                               <input 
                                 type="number" 
                                 value={age || ''} 
                                 onChange={(e) => {
                                   const val = e.target.value ? parseInt(e.target.value) : null
                                   setAge(val)
                                   fetchSegment(startTime)
                                 }}
                                 className="w-10 bg-muted/50 border border-border/20 rounded text-[9px] px-1 text-center"
                               />
                            </div>
                         </div>

                         {!analysisData?.normative?.normative_allowed ? (
                            <div className="p-3 bg-muted/10 border border-dashed border-border/40 rounded flex flex-col gap-2">
                               <p className="text-[9px] text-muted-foreground italic text-center">
                                  {analysisData?.normative?.reason || "Comparison N/A."}
                               </p>
                            </div>
                         ) : (
                            <div className="space-y-3">
                               <div className="p-2 bg-primary/5 border border-primary/20 rounded-md">
                                  <p className="text-[10px] text-foreground/90 leading-tight font-semibold text-center">
                                     {analysisData.normative.summary.pattern_hint}
                                  </p>
                               </div>

                               <div className="grid grid-cols-2 gap-2">
                                  {Object.entries(analysisData.normative.results.regional).slice(0, 4).map(([region, bands]: [any, any]) => {
                                     const topBand = Object.entries(bands).sort((a: any, b: any) => 
                                        Math.abs(b[1].z_score || 0) - Math.abs(a[1].z_score || 0)
                                     )[0] as [string, any];

                                     return (
                                       <div key={region} className="p-2 bg-muted/10 border border-border/40 rounded flex flex-col gap-1">
                                          <div className="flex items-center justify-between">
                                             <span className="text-[10px] font-bold text-muted-foreground uppercase">{region}</span>
                                          </div>
                                          <div className="flex items-baseline justify-between py-0.5">
                                             <span className="text-xs font-mono font-bold tracking-tighter">Z: {topBand[1].z_score?.toFixed(2) || '0.0'}</span>
                                             <div className={topBand[1].z_score > 0 ? 'text-red-400' : 'text-blue-400'}>
                                                {topBand[1].z_score > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                             </div>
                                          </div>
                                       </div>
                                     )
                                  })}
                               </div>
                               <p className="text-[8px] text-muted-foreground/60 italic text-center leading-tight">
                                  {analysisData.normative.summary.not_clinical_warning}
                                </p>
                            </div>
                         )}
                      </div>

                      {/* Region/Channel Details Stack */}
                      <div className="space-y-6 pt-2">
                         <div className="space-y-3">
                            <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest px-1">
                               <LayoutGrid className="w-3 h-3" /> Regional Dominance
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                               {qeeg.regional_metrics.map((reg: any) => (
                                 <div key={reg.region} className="p-2 bg-muted/10 border border-border/40 rounded">
                                    <div className="flex justify-between items-center mb-1">
                                       <span className="text-[10px] font-bold text-foreground/80">{reg.region}</span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                       <span className="text-xs font-mono font-bold text-primary">{reg.dominant_band.toUpperCase()}</span>
                                       <span className="text-[10px] font-mono">{(reg.relative_power[reg.dominant_band] * 100).toFixed(1)}%</span>
                                    </div>
                                 </div>
                               ))}
                            </div>
                         </div>

                         {qeeg.asymmetry_metrics.length > 0 && (
                           <div className="space-y-3">
                              <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest px-1">
                                 <Scale className="w-3 h-3" /> Alpha Asymmetry
                              </div>
                              <div className="space-y-1.5">
                                 {qeeg.asymmetry_metrics.map((asym: any) => (
                                   <div key={asym.pair} className="flex items-center gap-3 p-2 bg-muted/20 border border-border/30 rounded-md">
                                      <div className="w-10 text-[10px] font-mono font-bold text-muted-foreground">{asym.pair}</div>
                                      <div className="flex-1 h-2 bg-muted rounded-full relative overflow-hidden">
                                         <div 
                                           className={`absolute h-full transition-all duration-700 ${asym.bands.alpha.log_asymmetry > 0 ? 'right-1/2 bg-blue-500' : 'left-1/2 bg-indigo-500'}`}
                                           style={{ width: `${Math.min(Math.abs(asym.bands.alpha.log_asymmetry) * 10, 45)}%` }}
                                         ></div>
                                      </div>
                                      <div className="w-10 text-right text-[10px] font-mono font-bold">
                                         {Math.abs(asym.bands.alpha.log_asymmetry).toFixed(1)}
                                      </div>
                                   </div>
                                 ))}
                              </div>
                           </div>
                         )}

                         <div className="space-y-3">
                            <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest px-1">Channel Quantification</div>
                            <div className="border border-border/30 rounded-md overflow-hidden text-[10px]">
                               <div className="grid grid-cols-5 gap-2 px-2 py-1.5 bg-muted/50 font-bold text-muted-foreground uppercase text-[8px]">
                                  <div>Channel</div><div>D</div><div>T</div><div>A</div><div>B</div>
                               </div>
                               <div className="max-h-40 overflow-y-auto">
                                 {qeeg.channel_metrics.map((ch: any) => (
                                   <div key={ch.channel} className="grid grid-cols-5 gap-2 px-2 py-1.5 border-t border-border/20 font-mono items-center hover:bg-muted/10">
                                      <div className="font-bold">{ch.channel}</div>
                                      <div>{(ch.relative_power.delta * 10).toFixed(0)}</div>
                                      <div>{(ch.relative_power.theta * 10).toFixed(0)}</div>
                                      <div className={ch.dominant_band === 'alpha' ? 'text-primary' : ''}>{(ch.relative_power.alpha * 10).toFixed(0)}</div>
                                      <div>{(ch.relative_power.beta * 10).toFixed(0)}</div>
                                    </div>
                                 ))}
                               </div>
                            </div>
                         </div>
                      </div>
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
