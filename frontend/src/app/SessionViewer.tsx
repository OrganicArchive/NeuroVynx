import React, { useState, useEffect, useRef } from 'react'
import { ArrowLeft, ChevronLeft, ChevronRight, ChevronDown, Activity, AlertTriangle, BarChart3, Database, Brain, LayoutGrid, TrendingUp, TrendingDown, Minus, Trash2, Camera, Clock, Info, User2, Zap, Puzzle } from 'lucide-react'
import EegCanvasViewer from '../features/viewer/EegCanvasViewer'
import ArtifactTimeline from '../features/viewer/ArtifactTimeline'
import BrainTopomap from '../features/qeeg/BrainTopomap'

/**
 * SessionViewer: Orchestration Controller (Main Dashboard)
 * =======================================================
 * The central controller for the NeuroVynx analytical loop.
 * 
 * Design Architecture:
 * - Stateless Analysis Loop: Every 'FetchSegment' triggers a fresh end-to-end 
 *   DSP pipeline (Quality -> qEEG -> Normative -> Interpretation). This ensures 
 *   side-effect-free analysis at every 10-second epoch.
 * - Snapshot Management: Captures and persists the 'State' of a given window 
 *   (including interpretation strings and patterns) to allow for asynchronous 
 *   longitudinal review.
 * - UI/Logic Decoupling: Consolidates the technical DSP metrics into a 
 *   sidebar while prioritizing high-fidelity signal traces in the primary viewport.
 */

interface SessionViewerProps {
  sessionId: string
  onBack: () => void
}

const STANDARD_19 = [
  'Fp1', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8', 'T3', 'C3', 'Cz', 'C4', 'T4', 'T5', 'P3', 'Pz', 'P4', 'T6', 'O1', 'O2'
]

const GAIN_PRESETS = [1.0, 2.0, 5.0]
const SPACING_PRESETS = [0.5, 1.0, 1.5, 2.0, 3.0]

const SessionViewer: React.FC<SessionViewerProps> = ({ sessionId, onBack }) => {
  const [analysisData, setAnalysisData] = useState<any>(null)
  const [recordingAnalysis, setRecordingAnalysis] = useState<any>(null)
  const [recordingLoading, setRecordingLoading] = useState<boolean>(false)
  const [timelineData, setTimelineData] = useState<any>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  
  // UI Controls State
  const [startTime, setStartTime] = useState<number>(0)
  const [duration] = useState<number>(10) // Fixed to 10s pages for MVP Phase
  const [scaleFactor, setScaleFactor] = useState<number>(1.5) // Adjust amplitude
  const [channelSpacing, setChannelSpacing] = useState<number>(1.0)
  
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
  const [ageInputValue, setAgeInputValue] = useState<string>("25")
  const [mapMode, setMapMode] = useState<'relative' | 'normative'>('relative')
  const [selectedMontage, setSelectedMontage] = useState<'full' | 'standard'>('full')
  const [topoScaleMode, setTopoScaleMode] = useState<'auto' | 'fixed'>('auto')
  const [snapshots, setSnapshots] = useState<any[]>([])
  const [isAutoScrolling, setIsAutoScrolling] = useState<boolean>(false)
  const autoScrollRef = useRef<ReturnType<typeof setInterval> | null>(null)

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
      const confirmSave = window.confirm("[!] This segment contains quality warnings or artifacts. Using it as a baseline may bias future analysis. Use anyway?")
      if (!confirmSave) return
    } else {
       const confirmSave = window.confirm("Use current 10s segment as the normative reference for this session?")
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
          features: analysisData.features,
          metadata
        })
      })

      if (res.ok) {
        alert("Baseline updated successfully.")
        fetchSegment(startTime) // Refresh to apply comparison
      }
    } catch (err) {
      console.error(err)
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

  const handleTakeSnapshot = () => {
    if (!analysisData) return
    const newSnapshot = {
      id: Date.now(),
      startTime,
      duration,
      scaleFactor,
      channelSpacing,
      selectedMontage,
      topoScaleMode,
      timestamp: new Date().toISOString(),
      summary: (
        analysisData.interpretation?.summary?.short ||
        analysisData.quality?.summary ||
        (analysisData.features?.dominant_band
          ? ('Dominant band: ' + analysisData.features.dominant_band)
          : 'No summary available for this window.')
      ),
      topPatterns: (
        analysisData.interpretation?.top_patterns ||
        analysisData.quality?.warnings ||
        []
      )
    }
    setSnapshots(prev => [newSnapshot, ...prev].slice(0, 10))
  }

  const handleLoadSnapshot = (snap: any) => {
    setStartTime(snap.startTime)
    setScaleFactor(snap.scaleFactor)
    setChannelSpacing(snap.channelSpacing)
    setSelectedMontage(snap.selectedMontage)
    setTopoScaleMode(snap.topoScaleMode)
    fetchSegment(snap.startTime)
  }

  const handleRemoveSnapshot = (id: number) => {
    setSnapshots(prev => prev.filter(s => s.id !== id))
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

  const fetchRecordingAnalysis = async () => {
    setRecordingLoading(true)
    try {
      const res = await fetch(`http://localhost:8000/api/v1/sessions/${sessionId}/analysis/recording`)
      if (!res.ok) throw new Error("Failed to load recording analysis")
      const data = await res.json()
      setRecordingAnalysis(data)
    } catch (err) {
      console.error(err)
    } finally {
      setRecordingLoading(false)
    }
  }

  // Debounce age input
  useEffect(() => {
    const timer = setTimeout(() => {
       const parsed = ageInputValue ? parseInt(ageInputValue) : null
       setAge(parsed)
    }, 400); // 400ms debounce as recommended in Phase 20A
    return () => clearTimeout(timer);
  }, [ageInputValue]);

  // Initial Data Load
  useEffect(() => {
    fetchTimeline()
    fetchRecordingAnalysis()
    
    fetch(`http://localhost:8000/api/v1/sessions/${sessionId}`)
      .then(res => res.json())
      .then(data => {
        if (data.recording_context) {
          setRecordingContext(data.recording_context)
        }
        if (data.subject_age) {
          setAge(data.subject_age)
          setAgeInputValue(String(data.subject_age))
        }
      })
  }, [sessionId])

  // Reactive Analysis Trigger (Age, Context, Notch, Bandpass)
  useEffect(() => {
    fetchSegment(startTime)
  }, [sessionId, age, recordingContext, applyNotch, applyBandpass])

  // Auto-scroll: steps forward by one window every 10s. Pauses when loading.
  useEffect(() => {
    if (isAutoScrolling) {
      autoScrollRef.current = setInterval(() => {
        if (!loading) {
          fetchSegment(startTime + duration)
        }
      }, 10000)
    } else {
      if (autoScrollRef.current) {
        clearInterval(autoScrollRef.current)
        autoScrollRef.current = null
      }
    }
    return () => {
      if (autoScrollRef.current) clearInterval(autoScrollRef.current)
    }
  }, [isAutoScrolling, loading, startTime, duration])

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

  const unfilteredW = analysisData?.window
  const q = analysisData?.quality
  const qeeg = analysisData?.qeeg
  const f = analysisData?.features
  const b = analysisData?.baseline_comparison

  // Montage Filtering Logic
  const filteredIndices = unfilteredW ? unfilteredW.channels.reduce((acc: number[], ch: string, idx: number) => {
    if (selectedMontage === 'full') {
      acc.push(idx)
    } else if (STANDARD_19.includes(ch)) {
      acc.push(idx)
    }
    return acc
  }, []) : []

  const w = unfilteredW ? {
    ...unfilteredW,
    channels: filteredIndices.map((i: number) => unfilteredW.channels[i]),
    data: filteredIndices.map((i: number) => unfilteredW.data[i])
  } : null

  const availableCount = w?.channels.length || 0
  const expectedCount = selectedMontage === 'full' ? (unfilteredW?.channels.length || 0) : STANDARD_19.length

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

          {/* Montage Selector */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Montage</span>
            <div className="flex bg-muted/50 p-1 rounded-md border border-border/50">
              <button 
                onClick={() => setSelectedMontage('full')}
                className={`text-[10px] px-3 py-1 rounded transition-all font-bold ${
                  selectedMontage === 'full' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Full
              </button>
              <button 
                onClick={() => setSelectedMontage('standard')}
                className={`text-[10px] px-3 py-1 rounded transition-all font-bold ${
                  selectedMontage === 'standard' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                10-20
              </button>
            </div>
          </div>

          <div className="h-6 w-px bg-border mx-2"></div>

          {/* Gain Presets */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Gain</span>
            <div className="flex bg-muted/50 p-1 rounded-md border border-border/50">
              {GAIN_PRESETS.map(p => (
                <button 
                  key={p}
                  onClick={() => setScaleFactor(p)}
                  className={`text-[10px] px-3 py-1 rounded transition-all font-bold ${
                    scaleFactor === p ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  x{p}
                </button>
              ))}
            </div>
          </div>

          <div className="h-6 w-px bg-border mx-2"></div>

          {/* Spacing Presets */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Spacing</span>
            <div className="flex bg-muted/50 p-1 rounded-md border border-border/50">
              {SPACING_PRESETS.map(p => (
                <button 
                  key={p}
                  onClick={() => setChannelSpacing(p)}
                  className={`text-[10px] px-2 py-1 rounded transition-all font-bold ${
                    channelSpacing === p ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {p}x
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden flex flex-col p-4 gap-4">
        
        {/* Playback & Time Controls */}
        <div className="flex items-center justify-center gap-4 py-2 shrink-0">
          <button 
            onClick={() => { setIsAutoScrolling(false); fetchSegment(Math.max(0, startTime - duration)) }}
            disabled={startTime === 0 || loading}
            className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 text-secondary-foreground rounded disabled:opacity-50"
          >
            <ChevronLeft className="w-4 h-4" /> Previous 10s
          </button>

          {/* Auto-Scroll Play/Pause */}
          <button
            onClick={() => setIsAutoScrolling(prev => !prev)}
            disabled={loading}
            className={`flex items-center gap-2 px-4 py-2 rounded font-bold text-sm transition-all ${
              isAutoScrolling
                ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/30 animate-pulse'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            {isAutoScrolling ? (
              <><Minus className="w-4 h-4" /> Pause</>
            ) : (
              <><Activity className="w-4 h-4" /> Auto-Scroll</>
            )}
          </button>

          <span className="font-mono text-sm px-4 py-2 bg-muted rounded text-center w-[180px]">
            {startTime.toFixed(1)}s - {(startTime + duration).toFixed(1)}s
          </span>
          <button 
            onClick={() => { setIsAutoScrolling(false); fetchSegment(startTime + duration) }}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 text-secondary-foreground rounded disabled:opacity-50"
          >
           Next 10s <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Viewer and Analytical Panels Layout */}
        <div className="flex-1 flex gap-4 min-h-0">
          
          {/* Left Waveform Panel */}
          <div className="flex-1 bg-card border border-border rounded-lg relative overflow-hidden flex flex-col group min-h-0">
            {/* Status Overlays */}
            {error && (
              <div className="absolute inset-0 flex items-center justify-center bg-destructive/10 z-20 backdrop-blur-md">
                <div className="bg-background/90 border border-destructive/50 p-6 rounded-xl shadow-2xl flex flex-col items-center gap-4 max-w-md text-center">
                  <AlertTriangle className="w-12 h-12 text-destructive animate-pulse" />
                  <div>
                    <h3 className="text-lg font-bold text-destructive mb-1">Signal Interruption</h3>
                    <p className="text-sm text-muted-foreground">{error}</p>
                  </div>
                  <button 
                    onClick={() => fetchSegment(startTime)}
                    className="px-6 py-2 bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-all font-bold text-sm"
                  >
                    Retry Connection
                  </button>
                </div>
              </div>
            )}

            {loading && !analysisData && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-20 backdrop-blur-sm">
                <span className="animate-pulse font-mono flex items-center gap-2">
                  <Activity className="w-4 h-4 animate-bounce" /> Analyzing segment...
                </span>
              </div>
            )}


            <div className="shrink-0 flex items-center justify-between px-4 py-2 border-b border-border/30 bg-muted/10">
              <div className="flex items-center gap-3">
                 <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                  availableCount < expectedCount ? 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20' : 'bg-primary/10 text-primary border border-primary/20'
                 }`}>
                   {availableCount}/{expectedCount} Channels Accessible
                 </span>
                 {availableCount < expectedCount && (
                   <span className="text-[9px] text-muted-foreground italic">
                     ({expectedCount - availableCount} missing from source)
                   </span>
                 )}
              </div>
              <button
                onClick={handleTakeSnapshot}
                disabled={loading || !analysisData}
                className="bg-primary/90 hover:bg-primary text-primary-foreground px-4 py-1.5 rounded-full shadow-lg flex items-center gap-2 transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
              >
                <Camera className="w-3 h-3" />
                <span className="text-[10px] font-bold uppercase tracking-wider">Take Snapshot</span>
              </button>
            </div>

            <div className="w-full h-full overflow-y-auto overflow-x-hidden">
               {w && w.data && w.data.length > 0 && (
                <EegCanvasViewer 
                  data={w.data}
                  channels={w.channels || []}
                  sampleRate={w.sample_rate || 256}
                  verticalScaleFactor={scaleFactor}
                  spacingFactor={channelSpacing}
                  qualityData={q?.per_channel_status}
                />
              )}
            </div>
          </div>

          {/* Right Analytical Panel Sidebar (Consolidated) */}
          <div className="w-96 flex flex-col gap-6 overflow-y-auto overflow-x-hidden shrink-0 pr-2 pb-20">
            
            {/* -1. Analytics Context (Phase 20A Restoration) */}
            <div className="shrink-0 bg-card border border-border rounded-lg flex flex-col overflow-hidden shadow-md">
               <div className="px-4 py-2.5 border-b border-border bg-muted/30 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                     <User2 className="w-3.5 h-3.5 text-muted-foreground" />
                     <span className="font-bold text-[10px] uppercase tracking-widest text-muted-foreground">Subject Context</span>
                  </div>
                  <div className="flex items-center gap-1 text-[9px] text-muted-foreground italic">
                     <Info size={10} />
                     Used for normative gating
                  </div>
               </div>
               <div className="p-4 grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5">
                     <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">Subject Age</label>
                     <div className="relative">
                        <input 
                           type="number" 
                           value={ageInputValue} 
                           onChange={(e) => setAgeInputValue(e.target.value)}
                           className="w-full bg-muted/50 border border-border/50 rounded-md py-1.5 px-3 text-sm font-bold focus:ring-1 focus:ring-primary outline-none transition-all"
                           placeholder="Age..."
                        />
                        <span className="absolute right-3 top-2 text-[10px] text-muted-foreground opacity-50">YRS</span>
                     </div>
                  </div>
                  <div className="flex flex-col gap-1.5">
                     <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">State</label>
                     <select 
                        value={recordingContext}
                        onChange={(e) => setRecordingContext(e.target.value)}
                        className="w-full bg-muted/50 border border-border/50 rounded-md py-1.5 px-3 text-sm font-bold focus:ring-1 focus:ring-primary outline-none transition-all cursor-pointer"
                     >
                        <option value="awake">Awake</option>
                        <option value="drowsy">Drowsy</option>
                        <option value="sleep">Sleep</option>
                     </select>
                  </div>
               </div>
            </div>

            {/* 0. Temporal Dynamics (Phase 5.1 Analysis) */}
            <div className="shrink-0 bg-card border border-border rounded-lg flex flex-col overflow-hidden shadow-md">
               <div className="px-4 py-3 border-b border-border bg-primary/10 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                     <TrendingUp className="w-4 h-4 text-primary" />
                     <span className="font-bold text-[11px] uppercase tracking-wider text-primary">Temporal Dynamics</span>
                  </div>
                  {recordingAnalysis?.overall_confidence_level && (
                     <div className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                        recordingAnalysis.overall_confidence_level === 'high' ? 'bg-green-500/10 text-green-500 border-green-500/20' :
                        recordingAnalysis.overall_confidence_level === 'moderate' ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' :
                        'bg-red-500/10 text-red-500 border-red-500/20'
                     }`}>
                        {recordingAnalysis.overall_confidence_level.toUpperCase()} CONFIDENCE
                     </div>
                  )}
               </div>
               <div className="p-4 space-y-4">
                  {recordingLoading ? (
                     <div className="py-8 text-center border border-dashed border-border/40 rounded-lg bg-muted/5 font-mono">
                        <Activity className="w-6 h-6 text-primary animate-bounce mx-auto mb-2" />
                        <p className="text-[10px] text-muted-foreground italic tracking-tight uppercase">Sampling recording windows...</p>
                     </div>
                  ) : recordingAnalysis ? (
                     <>
                        <p className="text-[13px] leading-relaxed text-foreground font-semibold italic">
                           "{recordingAnalysis.temporal_summary?.short}"
                        </p>
                        
                        <div className="flex flex-wrap gap-1.5">
                           {(recordingAnalysis.temporal_patterns || []).slice(0, 5).map((p: any) => (
                              <div key={p.pattern_label} className="flex items-center bg-muted/30 border border-border/50 rounded overflow-hidden">
                                 <span className="px-2 py-0.5 text-[9px] font-bold uppercase truncate max-w-[120px]">
                                    {p.pattern_label}
                                 </span>
                                 <span className={`px-1.5 py-0.5 text-[8px] font-black border-l border-border/50 ${
                                    p.temporal_classification === 'PERSISTENT' ? 'text-green-500' :
                                    p.temporal_classification === 'INTERMITTENT' ? 'text-yellow-500' :
                                    p.temporal_classification === 'ARTIFACT-LINKED' ? 'text-red-400' :
                                    'text-blue-400'
                                 }`}>
                                    {p.temporal_classification}
                                 </span>
                              </div>
                           ))}
                        </div>

                        {recordingAnalysis.caveats?.length > 0 && (
                           <div className="space-y-1 pt-2 border-t border-border/40">
                              {recordingAnalysis.caveats.map((c: string, i: number) => (
                                 <div key={i} className="flex items-start gap-1.5 text-[10px] text-yellow-600/80 italic leading-tight">
                                    <AlertTriangle className="w-2.5 h-2.5 shrink-0 mt-0.5" /> {c}
                                 </div>
                              ))}
                           </div>
                        )}
                     </>
                  ) : (
                     <div className="py-4 text-center">
                        <button 
                           onClick={fetchRecordingAnalysis}
                           className="text-[10px] font-bold text-primary hover:underline uppercase tracking-widest"
                        >
                           Run Recording Analysis
                        </button>
                     </div>
                  )}
               </div>
            </div>

            {/* 1. Interpretive Insights (Phase 9.6 Alignment) */}
            <div className="shrink-0 bg-card border border-border rounded-lg flex flex-col overflow-hidden shadow-sm">
               <div className="px-4 py-3 border-b border-border bg-primary/5 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                     <Brain className="w-4 h-4 text-primary" />
                     <span className="font-bold text-[11px] uppercase tracking-wider text-primary/80">Interpretive Insights</span>
                  </div>
                  {analysisData?.interpretation?.confidence_score !== undefined && (
                     <div className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                        (analysisData?.interpretation?.confidence?.global_score ?? 0) > 0.7 ? 'bg-green-500/10 text-green-500 border-green-500/20' :
                        (analysisData?.interpretation?.confidence?.global_score ?? 0) > 0.4 ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' :
                        'bg-red-500/10 text-red-500 border-red-500/20'
                     }`}>
                        {(analysisData?.interpretation?.confidence?.global_score ?? 0) > 0.7 ? 'HIGH' :
                         (analysisData?.interpretation?.confidence?.global_score ?? 0) > 0.4 ? 'MODERATE' : 'LOW'} CONFIDENCE
                     </div>
                  )}
               </div>
               <div className="p-4">
                  <InterpretationPanel data={analysisData} loading={loading} />
               </div>
            </div>

            {/* 2. Snapshot Gallery (Moved inside Sidebar) */}
            <div className="shrink-0 bg-card border border-border rounded-lg flex flex-col overflow-hidden shadow-sm">
               <div className="px-4 py-3 bg-muted/30 border-b border-border flex items-center justify-between">
                  <div className="flex items-center gap-2 text-primary/80">
                     <Camera className="w-4 h-4" />
                     <span className="text-[11px] font-bold uppercase tracking-widest">Snapshot Gallery</span>
                  </div>
                  <span className="bg-muted px-2 py-0.5 rounded-full text-[9px] font-mono text-muted-foreground">{snapshots.length}/10</span>
               </div>

               <div className="max-h-64 overflow-y-auto p-4 space-y-3">
                  {snapshots.length === 0 ? (
                    <div className="py-6 text-center border border-dashed border-border/40 rounded-lg">
                       <Clock className="w-5 h-5 text-muted-foreground/20 mx-auto mb-2" />
                       <p className="text-[10px] text-muted-foreground italic">No snapshots for this session.</p>
                    </div>
                  ) : (
                    snapshots.map(snap => (
                      <div key={snap.id} className="group relative bg-muted/10 border border-border/40 hover:border-primary/30 rounded-lg p-3 transition-all">
                         <div className="flex justify-between items-start mb-1.5">
                            <div className="flex flex-col gap-0.5">
                               <span className="text-[10px] font-bold font-mono text-foreground/90">
                                  t={snap.startTime.toFixed(1)}s -- {snap.selectedMontage.toUpperCase()} / {snap.scaleFactor.toFixed(1)}x
                               </span>
                               <span className="text-[8px] text-muted-foreground">{new Date(snap.timestamp).toLocaleTimeString()}</span>
                            </div>
                            <button
                              onClick={() => handleRemoveSnapshot(snap.id)}
                              className="opacity-0 group-hover:opacity-100 p-1 hover:text-destructive transition-all"
                            >
                               <Trash2 className="w-3 h-3" />
                            </button>
                         </div>

                         <p className="text-[10px] text-muted-foreground line-clamp-2 mt-1 italic">
                            "{typeof snap.summary === 'string' ? snap.summary : snap.summary?.short}"
                         </p>

                         <div className="flex items-center justify-between gap-2 border-t border-border/20 pt-2">
                            <div className="flex gap-1 flex-wrap">
                               {Array.from(snap.topPatterns as string[]).slice(0, 2).map((p: string) => (
                                 <span key={p} className="text-[7px] px-1.5 py-0.5 bg-primary/5 text-primary border border-primary/10 rounded-full uppercase font-bold">
                                    {p}
                                 </span>
                               ))}
                            </div>
                            <button
                              onClick={() => handleLoadSnapshot(snap)}
                              className="text-[10px] font-bold text-primary hover:underline shrink-0"
                            >
                               Jump back
                            </button>
                         </div>
                      </div>
                    ))
                  )}
               </div>
            </div>

            {/* 2.5 Plugin Insights (Phase 19 Implementation) */}
            {analysisData?.plugin_results?.length > 0 && (
              <div className="shrink-0 bg-card border border-border rounded-lg flex flex-col overflow-hidden shadow-md">
                <div className="px-4 py-3 border-b border-border bg-purple-500/10 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Puzzle className="w-4 h-4 text-purple-400" />
                    <span className="font-bold text-[11px] uppercase tracking-wider text-purple-400">Plugin Insights</span>
                  </div>
                </div>
                <div className="p-4 space-y-6">
                  {analysisData.plugin_results.map((plugin: any, idx: number) => (
                    <div key={plugin.plugin_id + idx} className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex flex-col">
                          <span className="text-[10px] font-bold text-foreground flex items-center gap-1.5">
                            {plugin.plugin_id.split('.').pop()?.replace('_', ' ')}
                            <span className="text-[8px] font-mono text-muted-foreground opacity-60">v{plugin.version}</span>
                          </span>
                          <span className="text-[8px] font-mono text-muted-foreground uppercase">{plugin.category}</span>
                        </div>
                        <TrustTierBadge tier={plugin.trust_tier} />
                      </div>
                      
                      <div className="bg-muted/10 border border-border/20 rounded-lg overflow-hidden">
                        <PluginRenderer output={plugin} />
                      </div>
                      
                      {idx < analysisData.plugin_results.length - 1 && (
                        <div className="pt-4 border-b border-white/5" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3. Spectral Features */}
            <div className="shrink-0 bg-card border border-border rounded-lg flex flex-col overflow-hidden shadow-sm">
               <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
                 <BarChart3 className="w-4 h-4 text-primary" />
                 <span className="font-bold text-[11px] uppercase tracking-wider text-primary/80">Spectral Features</span>
               </div>
               <div className="p-4 space-y-4">
                  {!f || !f.global_summary ? (
                     <span className="text-xs text-muted-foreground animate-pulse font-mono tracking-tighter uppercase">Analyzing...</span>
                  ) : (
                    <div className="space-y-2.5">
                      {['delta', 'theta', 'alpha', 'beta'].map(band => {
                        const val = f?.global_summary?.[`mean_relative_${band}`] ?? 0;
                        return (
                          <div key={band} className="flex justify-between items-center text-[11px]">
                            <span className="capitalize text-muted-foreground font-bold w-12">{band}</span>
                            <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                              <div className="h-full bg-primary" style={{ width: `${Math.min(val * 100, 100)}%` }}></div>
                            </div>
                            <span className="font-mono text-[10px] w-10 text-right font-bold">{(val * 100).toFixed(0)}%</span>
                          </div>
                        )
                      })}
                    </div>
                  )}
               </div>
            </div>

            {/* 4. Baseline Status */}
            <div className="shrink-0 bg-card border border-border rounded-lg flex flex-col overflow-hidden shadow-sm">
               <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                     <Database className="w-4 h-4 text-primary" />
                     <span className="font-bold text-[11px] uppercase tracking-wider text-primary/80">Baseline Status</span>
                  </div>
                  <button 
                     onClick={handleSaveBaseline}
                     className="text-[9px] font-bold text-primary hover:underline uppercase tracking-tighter"
                     disabled={isSavingBaseline || loading}
                  >
                     Update Reference
                  </button>
               </div>
               <div className="p-4">
                 {b?.error ? (
                    <div className="text-[10px] p-3 bg-muted/20 border border-dashed border-border rounded-lg text-muted-foreground italic text-center leading-relaxed">
                       No active baseline. Set current window as reference to enable live comparisons.
                    </div>
                 ) : (
                    <div className="space-y-4">
                       <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-muted-foreground uppercase">Confidence</span>
                          <span className={`text-[10px] font-mono font-bold ${b?.artifact_data?.comparison_confidence > 0.7 ? 'text-green-500' : 'text-yellow-500'}`}>
                             {((b?.artifact_data?.comparison_confidence || 0) * 100).toFixed(0)}%
                          </span>
                       </div>
                       <div className="space-y-2 border-t border-border/10 pt-3">
                          {b?.interpretation?.map((interp: string, idx: number) => (
                             <div key={idx} className="text-[11px] p-2 bg-primary/5 border border-primary/10 rounded-lg leading-relaxed font-medium italic">
                                "{interp}"
                             </div>
                          ))}
                       </div>
                    </div>
                 )}
               </div>
            </div>

            {/* 5. Quantitative EEG (qEEG) Board */}
            <div className="flex-1 bg-card border border-border rounded-lg flex flex-col overflow-hidden shadow-md min-h-[500px]">
               <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-primary" />
                    <span className="font-bold text-[11px] uppercase tracking-wider text-primary/80">Quantitative Board</span>
                  </div>
                  {qeeg?.is_available && (
                    <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold border ${
                      qeeg.trust_level === 'trusted' ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                    }`}>
                      {qeeg.trust_level.toUpperCase()}
                    </span>
                  )}
               </div>

               <div className="flex-1 overflow-y-auto p-4 space-y-8 custom-scrollbar">
                  {!qeeg || !qeeg.is_available ? (
                    <div className="py-12 text-center border border-dashed border-border/40 rounded-xl bg-muted/5">
                       <AlertTriangle className="w-8 h-8 text-yellow-500/20 mx-auto mb-3" />
                       <p className="text-[11px] text-muted-foreground italic leading-relaxed px-6">
                          {qeeg?.reason || "Initializing spatial and temporal metrics for this epoch..."}
                       </p>
                    </div>
                  ) : (
                    <div className="space-y-10">
                       
                       {/* 5A. Temporal Dynamics */}
                       <div className="space-y-4">
                          <div className="flex items-center justify-between border-b border-border/10 pb-2">
                             <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                <Activity className="w-3.5 h-3.5" /> Temporal Dynamics
                             </div>
                             {analysisData?.temporal_qeeg?.summary?.overall_stability && (
                                <div className={`text-[8px] px-1.5 py-0.5 rounded border font-bold ${
                                  analysisData.temporal_qeeg.summary.overall_stability === 'high' ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                                }`}>
                                  STABILITY: {analysisData?.temporal_qeeg?.summary?.overall_stability?.toUpperCase()}
                                </div>
                             )}
                          </div>

                          <div className="grid grid-cols-2 gap-2">
                             {['delta', 'theta', 'alpha', 'beta'].map(band => {
                                const trend = analysisData?.temporal_qeeg?.global_band_trends?.[band];
                                if (!trend) return null;
                                return (
                                  <div key={band} className="p-2 bg-muted/10 border border-border/40 rounded flex flex-col gap-1 hover:bg-muted/20 transition-colors">
                                     <div className="flex items-center justify-between">
                                        <span className="text-[10px] uppercase font-bold text-muted-foreground/70">{band}</span>
                                        {trend.trend === 'rising' ? <TrendingUp className="w-2.5 h-2.5 text-red-400" /> :
                                         trend.trend === 'falling' ? <TrendingDown className="w-2.5 h-2.5 text-blue-400" /> :
                                         <Minus className="w-2.5 h-2.5 text-muted-foreground/30" />}
                                     </div>
                                     <div className="text-xs font-mono font-bold">{(trend.current * 100).toFixed(1)}%</div>
                                  </div>
                                )
                             })}
                          </div>
                       </div>

                       {/* 5B. Scalp Topography */}
                       <div className="space-y-4">
                          <div className="flex items-center justify-between border-b border-border/10 pb-2">
                             <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                                 <div className="flex bg-muted/20 p-0.5 rounded border border-border/20">
                                    {['delta', 'theta', 'alpha', 'beta'].map(b => (
                                       <button 
                                         key={b}
                                         onClick={() => setSelectedTopoBand(b)}
                                         className={`text-[9px] px-2 py-0.5 rounded transition-all font-bold ${
                                           selectedTopoBand === b ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                                         }`}
                                       >
                                          {b[0].toUpperCase()}
                                       </button>
                                    ))}
                                 </div>
                                 <div className="h-4 w-px bg-border/40" />
                                 <div className="flex gap-1">
                                    <button 
                                       onClick={() => setMapMode('relative')}
                                       className={`text-[8px] px-2 py-0.5 rounded font-bold uppercase border transition-all ${
                                          mapMode === 'relative' ? 'bg-primary/20 border-primary/40 text-primary' : 'bg-background/40 border-border/20 text-muted-foreground'
                                       }`}
                                    >Rel</button>
                                    <button 
                                       onClick={() => setMapMode('normative')}
                                       disabled={!analysisData?.normative_topography?.is_available}
                                       className={`text-[8px] px-2 py-0.5 rounded font-bold uppercase border transition-all disabled:opacity-30 ${
                                          mapMode === 'normative' ? 'bg-primary/20 border-primary/40 text-primary' : 'bg-background/40 border-border/20 text-muted-foreground'
                                       }`}
                                    >Dev</button>
                                 </div>
                                 <div className="h-4 w-px bg-border/40" />
                                 <button 
                                    onClick={() => setTopoScaleMode(topoScaleMode === 'fixed' ? 'auto' : 'fixed')}
                                    className={`text-[8px] px-2 py-0.5 rounded font-bold uppercase border transition-all ${
                                       topoScaleMode === 'fixed' ? 'bg-primary/20 border-primary/40 text-primary' : 'bg-background/40 border-border/20 text-muted-foreground'
                                    }`}
                                 >
                                    {topoScaleMode === 'fixed' ? 'Fixed' : 'Auto'}
                                 </button>
                              </div>
                          </div>

                          <div className="relative bg-muted/5 rounded-xl border border-border/20 p-2 group shadow-inner flex items-center justify-center">
                             {mapMode === 'normative' && analysisData?.normative_topography?.is_available && analysisData?.normative_topography?.bands?.[selectedTopoBand] ? (
                                <BrainTopomap 
                                   gridData={analysisData.normative_topography.bands[selectedTopoBand].surface || []}
                                   electrodes={analysisData?.topography?.electrodes || []}
                                   trustLevel={analysisData.normative_topography.trust_level}
                                   metricLabel={selectedTopoBand.toUpperCase()}
                                   vMin={topoScaleMode === 'fixed' ? -3.0 : (analysisData.normative_topography.bands[selectedTopoBand].z_min ?? -3)}
                                   vMax={topoScaleMode === 'fixed' ? 3.0 : (analysisData.normative_topography.bands[selectedTopoBand].z_max ?? 3)}
                                   isLowVariance={false}
                                   mapType="normative_z_map"
                                   symmetricLimit={topoScaleMode === 'fixed' ? 3.0 : (analysisData.normative_topography.bands[selectedTopoBand].symmetric_limit ?? 3)}
                                />
                             ) : (
                                analysisData?.topography?.bands?.[selectedTopoBand] ? (
                                  <BrainTopomap 
                                     gridData={analysisData.topography.bands[selectedTopoBand].surface || []}
                                     electrodes={analysisData?.topography?.electrodes || []}
                                     trustLevel={analysisData?.topography?.trust_level || 'unavailable'}
                                     metricLabel={selectedTopoBand.toUpperCase()}
                                     vMin={analysisData.topography.bands[selectedTopoBand].v_min ?? 0}
                                     vMax={analysisData.topography.bands[selectedTopoBand].v_max ?? 1}
                                     isLowVariance={!!analysisData.topography.bands[selectedTopoBand].low_variance_mode}
                                     mapType="relative_power"
                                  />
                                ) : (
                                  <div className="flex items-center justify-center p-12 bg-muted/5 rounded-xl border border-dashed border-border/20 italic text-[10px] text-muted-foreground">
                                     Generating spatial metrics for {selectedTopoBand}...
                                  </div>
                                )
                             )}
                          </div>

                          <div className="p-3 bg-primary/5 border border-primary/10 rounded-lg text-center font-medium italic">
                             <div className="text-[10px] text-primary mb-0.5 uppercase not-italic font-bold tracking-tight">Pattern Insight</div>
                             <p className="text-[11px] leading-snug">
                                {mapMode === 'normative' 
                                   ? (analysisData?.normative_topography?.summary?.pattern_hint || "Normative deviation metrics unavailable for this slice.")
                                   : (analysisData?.topography?.summary?.pattern_hint || "Insufficient topography coverage for pattern detection.")
                                }
                             </p>
                          </div>
                       </div>

                       {/* 5C. Normative Analysis */}
                       <div className="space-y-4">
                          <div className="flex items-center justify-between border-b border-border/10 pb-2">
                             <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                <Database className="w-3.5 h-3.5" /> Normative Analysis
                             </div>
                          </div>

                          {!analysisData?.normative?.normative_allowed ? (
                             <div className="p-3 bg-muted/10 border border-dashed border-border/40 rounded italic text-center">
                                <p className="text-[10px] text-muted-foreground">
                                   {analysisData?.normative?.reason || "Comparison N/A."}
                                </p>
                             </div>
                          ) : (
                             <div className="space-y-3">
                                <div className="grid grid-cols-2 gap-2">
                                   {Object.entries(analysisData?.normative?.results?.regional ?? {}).slice(0, 4).map(([region, bands]: [any, any]) => {
                                      const topBand = Object.entries(bands).sort((a: any, b: any) => 
                                         Math.abs(b[1].z_score || 0) - Math.abs(a[1].z_score || 0)
                                      )[0] as [string, any];

                                      return (
                                        <div key={region} className="p-2.5 bg-muted/10 border border-border/40 rounded-lg flex flex-col gap-1 hover:bg-muted/20 transition-colors">
                                           <div className="flex items-center justify-between">
                                              <span className="text-[10px] font-bold text-muted-foreground uppercase">{region}</span>
                                           </div>
                                           <div className="flex items-baseline justify-between py-0.5">
                                              <span className="text-xs font-mono font-bold tracking-tighter">Z: {topBand[1].z_score?.toFixed(2) || '0.0'}</span>
                                              <div className={topBand[1].z_score > 0 ? 'text-red-400' : 'text-blue-400'}>
                                                 {topBand[1].z_score > 0 ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
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

                       {/* 5D. Regional Analysis */}
                       <div className="space-y-4">
                          <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest border-b border-border/10 pb-2">
                             <LayoutGrid className="w-3.5 h-3.5" /> Regional Distribution
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                             {qeeg.regional_metrics.map((reg: any) => (
                               <div key={reg.region} className="p-2.5 bg-muted/10 border border-border/40 rounded-lg flex flex-col gap-1.5">
                                  <div className="text-[9px] font-bold uppercase text-muted-foreground/60">{reg.region}</div>
                                  <div className="flex items-center justify-between">
                                     <span className="text-[11px] font-mono font-bold text-primary">{reg.dominant_band.toUpperCase()}</span>
                                     <span className="text-[10px] font-mono opacity-80">{(reg.relative_power[reg.dominant_band] * 100).toFixed(0)}%</span>
                                  </div>
                               </div>
                             ))}
                          </div>
                       </div>

                       {/* 5E. Channel Quantification */}
                       <div className="space-y-4">
                          <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-widest border-b border-border/10 pb-2">
                             <Activity className="w-3.5 h-3.5" /> Channel Quantification
                          </div>
                          <div className="border border-border/20 rounded-lg overflow-hidden bg-muted/5 shadow-inner">
                             <div className="grid grid-cols-5 gap-2 px-3 py-2 bg-muted/50 font-bold text-muted-foreground uppercase text-[8px] tracking-widest border-b border-border/10">
                                <div>CH</div><div>D</div><div>T</div><div>A</div><div>B</div>
                             </div>
                             <div className="max-h-48 overflow-y-auto custom-scrollbar">
                               {qeeg.channel_metrics.map((ch: any) => (
                                 <div key={ch.channel} className="grid grid-cols-5 gap-2 px-3 py-1.5 border-t border-border/5 font-mono items-center hover:bg-primary/5 transition-colors">
                                    <div className="font-bold text-foreground/80">{ch.channel}</div>
                                    <div className="opacity-50">{(ch.relative_power.delta * 10).toFixed(0)}</div>
                                    <div className="opacity-50">{(ch.relative_power.theta * 10).toFixed(0)}</div>
                                    <div className={ch.dominant_band === 'alpha' ? 'text-primary font-bold' : 'opacity-50'}>{(ch.relative_power.alpha * 10).toFixed(0)}</div>
                                    <div className="opacity-50">{(ch.relative_power.beta * 10).toFixed(0)}</div>
                                  </div>
                               ))}
                             </div>
                          </div>
                       </div>

                       {/* 5E. Library Calibration (Optional/Small) */}
                       <div className="pt-4 border-t border-border/20">
                          <div className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest mb-3 text-center">Library Calibration</div>
                          <div className="flex gap-2">
                             <select 
                               value={selectedArtifactLabel}
                               onChange={(e) => setSelectedArtifactLabel(e.target.value)}
                               className="flex-1 bg-muted/50 text-[10px] border border-border/30 rounded px-2 h-8"
                             >
                               {ARTIFACT_LABELS.map(opt => (
                                 <option key={opt.value} value={opt.value}>{opt.label}</option>
                               ))}
                             </select>
                             <button
                               onClick={handleSaveArtifact}
                               disabled={isSavingArtifact || loading}
                               className="px-4 bg-secondary text-secondary-foreground text-[10px] font-bold rounded hover:bg-secondary/80 h-8 transition-colors shrink-0 uppercase tracking-tighter"
                             >
                               {isSavingArtifact ? '...' : 'Store Template'}
                             </button>
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

/**
 * Hardened Interpretation Panel (Phase 20A)
 */
const InterpretationPanel = ({ data, loading }: { data: any, loading: boolean }) => {
  const status = data?.interpretation_status || (loading ? 'loading' : 'unavailable');
  const interpretation = data?.interpretation;
  const skipReason = data?.interpretation_skip_reason;

  if (status === 'loading') {
    return (
      <div className="py-8 text-center border border-dashed border-border/40 rounded-lg bg-muted/5 font-mono">
        <Clock className="w-5 h-5 text-primary/40 animate-spin mx-auto mb-2" />
        <p className="text-[10px] text-muted-foreground italic tracking-tight">GENERATING INTERPRETIVE CONTEXT...</p>
      </div>
    );
  }

  if (status === 'skipped') {
    return (
      <div className="p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-lg flex flex-col items-center gap-2 text-center">
        <AlertTriangle className="w-6 h-6 text-yellow-500/60" />
        <div>
           <p className="text-[11px] font-bold text-yellow-600/90 uppercase tracking-tighter">Interpretation Bypassed</p>
           <p className="text-[10px] text-yellow-700/70 italic mt-0.5">{skipReason || "Quality constraints prevented reliable synthesis."}</p>
        </div>
      </div>
    );
  }

  if (status === 'error' || !interpretation?.summary) {
     return (
        <div className="py-6 text-center border border-dashed border-border/40 rounded-lg bg-muted/5">
           <AlertTriangle className="w-5 h-5 text-muted-foreground/30 mx-auto mb-2" />
           <p className="text-[10px] text-muted-foreground italic tracking-tight uppercase">Interpretation Unavailable</p>
        </div>
     );
  }

  // READY STATE
  const s = interpretation.summary;
  const [showTech, setShowTech] = useState(false);

  return (
    <div className="space-y-4">
       {/* Confidence Banner */}
       {s.confidence_banner && (
          <div className="px-3 py-1.5 rounded bg-muted/30 border border-border/40 text-[10px] font-bold text-muted-foreground tracking-wide flex items-center gap-2">
             <div className={`w-1.5 h-1.5 rounded-full ${
                (interpretation.confidence?.global_score ?? 0) > 0.7 ? 'bg-green-500' :
                (interpretation.confidence?.global_score ?? 0) > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
             }`} />
             {s.confidence_banner.toUpperCase()}
          </div>
       )}

       {/* Primary Highlights */}
       <div className="space-y-3">
          <p className="text-[12px] leading-relaxed text-foreground/90 font-semibold italic">
             {s.primary_narrative}
          </p>
          <ul className="space-y-2.5">
             {(s.primary_points || []).map((point: string, idx: number) => (
                <li key={idx} className="relative pl-4 text-[12px] text-foreground/80 leading-snug">
                   <span className="absolute left-0 top-1.5 w-1.5 h-1.5 rounded-full bg-primary/40" />
                   {point}
                </li>
             ))}
          </ul>
       </div>

       {/* Secondary Findings */}
       {s.secondary_points?.length > 0 && (
          <div className="pt-3 border-t border-border/40 space-y-2">
             <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                Secondary Findings
             </span>
             <ul className="space-y-1">
                {s.secondary_points.map((point: string, idx: number) => (
                   <li key={idx} className="text-[11px] text-muted-foreground/90 italic flex items-start gap-1.5">
                      <ChevronRight className="w-3 h-3 shrink-0 mt-0.5" /> {point}
                   </li>
                ))}
             </ul>
          </div>
       )}

       {/* Technical Details Toggle */}
       <div className="mt-2 pt-2 border-t border-border/30">
          <button 
             onClick={() => setShowTech(!showTech)}
             className="flex items-center gap-1.5 text-[9px] font-bold text-muted-foreground/60 uppercase tracking-widest hover:text-primary transition-colors mb-2"
          >
             {showTech ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
             Technical Audit ({s.technical_items_count + s.suppressed_items_count} items)
          </button>
          
          {showTech && (
             <div className="space-y-3 bg-muted/5 p-3 rounded-md border border-border/10 animate-in fade-in slide-in-from-top-1">
                <p className="text-[10px] text-muted-foreground italic leading-tight">
                   {s.technical_note}
                </p>
                <div className="grid grid-cols-2 gap-2">
                   <div className="flex flex-col p-2 bg-muted/20 rounded border border-border/5">
                      <span className="text-[8px] text-muted-foreground uppercase font-bold text-center">Tech Findings</span>
                      <span className="text-[12px] font-mono font-bold text-foreground text-center">
                         {s.technical_items_count}
                      </span>
                   </div>
                   <div className="flex flex-col p-2 bg-muted/20 rounded border border-border/5">
                      <span className="text-[8px] text-muted-foreground uppercase font-bold text-center">Suppressed</span>
                      <span className="text-[12px] font-mono font-bold text-foreground text-center">
                         {s.suppressed_items_count}
                      </span>
                   </div>
                </div>
             </div>
          )}
       </div>

       {interpretation?.caveats?.length > 0 && (
          <div className="mt-2 pt-2 border-t border-border/40">
             <div className="space-y-1">
                {interpretation.caveats.map((c: string, i: number) => (
                   <div key={i} className="flex items-center gap-1.5 text-[10px] text-yellow-600/80 italic leading-tight">
                      <AlertTriangle className="w-2.5 h-2.5" /> {c}
                   </div>
                ))}
             </div>
          </div>
       )}
    </div>
  );
};

/**
 * Standard templates for Phase 19 Plugin Visualization.
 */
const PluginRenderer = ({ output }: { output: any }) => {
  if (output.status === 'failed') {
    return (
      <div className="p-3 text-[10px] text-red-400 italic bg-red-400/5 flex items-start gap-2">
        <AlertTriangle size={12} className="shrink-0 mt-0.5" />
        <span>Failed: {output.error_message}</span>
      </div>
    );
  }

  const result = output.result;
  if (!result) return <div className="p-3 text-[10px] text-muted-foreground italic">No result returned</div>;

  const template = result.template || 'json';
  const data = result.data;

  switch (template) {
    case 'key-value':
      return (
        <div className="p-3 space-y-1.5">
          {Object.entries(data || {}).map(([key, val]: [string, any]) => (
            <div key={key} className="flex justify-between items-center text-[10px]">
              <span className="text-muted-foreground font-medium">{key}</span>
              <span className="font-mono font-bold text-foreground">
                {typeof val === 'number' ? val.toFixed(3) : String(val)}
              </span>
            </div>
          ))}
        </div>
      );

    case 'table':
      return (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[9px] border-collapse">
            <thead>
              <tr className="bg-muted/30 border-b border-border/20">
                {(data?.headers || []).map((h: string) => (
                  <th key={h} className="px-2 py-1.5 font-bold uppercase tracking-wider text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data?.rows || []).map((row: any[], i: number) => (
                <tr key={i} className="border-b border-border/10 hover:bg-white/5 transition-colors">
                  {row.map((cell, j) => (
                    <td key={j} className="px-2 py-1.5 font-mono text-foreground/80">{String(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    case 'json':
    default:
      return (
        <div className="p-3 bg-black/20 font-mono text-[9px] text-muted-foreground">
          <pre className="whitespace-pre-wrap">{JSON.stringify(data || result, null, 2)}</pre>
        </div>
      );
  }
};

const TrustTierBadge = ({ tier }: { tier: string }) => {
  const tiers: Record<string, { label: string; color: string }> = {
    core_certified: { label: 'Certified', color: 'text-blue-400 border-blue-400/30 bg-blue-400/10' },
    official_experimental: { label: 'Experimental', color: 'text-purple-400 border-purple-400/30 bg-purple-400/10' },
    community_reviewed: { label: 'Community', color: 'text-green-400 border-green-400/30 bg-green-400/10' },
    unverified_local: { label: 'Local', color: 'text-orange-400 border-orange-400/30 bg-orange-400/10' },
  };

  const config = tiers[tier] || tiers.unverified_local;

  return (
    <span className={`px-1.5 py-0.5 rounded border text-[8px] font-bold uppercase tracking-tighter ${config.color}`}>
      {config.label}
    </span>
  );
};

export default SessionViewer
