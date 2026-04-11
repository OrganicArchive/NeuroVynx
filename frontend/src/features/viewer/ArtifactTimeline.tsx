/**
 * ArtifactTimeline Component
 * =========================
 * 
 * Provides a global chronological 'Minimap' of the entire EEG recording.
 * 
 * This component visualizes the results of the backend's Global Scrubbing 
 * pass, mapping technical quality scores and artifact markers into a 
 * single interactive track.
 * 
 * Core Features:
 * - Direct scrubbing (Time-skipping).
 * - Multi-level severity color rendering (Good/Warning/Bad).
 * - Real-time viewport synchronization.
 */

import React from 'react'

interface Marker {
  /** The type of artifact detected (e.g., 'blink', 'clipping') */
  type: string
  /** The specific electrodes affected */
  channels: string[]
}

interface Segment {
  /** Chronological start position in seconds */
  start: number
  /** Chronological end position in seconds */
  end: number
  /** Composite score from the quality engine (0-100) */
  quality_score: number
  /** Categorical impact of artifacts in this segment */
  severity: 'good' | 'warning' | 'bad'
  /** List of specific artifact markers identified */
  markers: Marker[]
}

interface TimelineProps {
  /** Array of pre-computed global segments */
  segments: Segment[]
  /** Total length of the EEG file in seconds */
  totalDuration: number
  /** The current start time of the main EEG viewer window */
  viewportStart: number
  /** The current width of the main EEG viewer window (typically 10s) */
  viewportDuration: number
  /** Callback to update the main viewer position */
  onJumpTo: (time: number) => void
}

const ArtifactTimeline: React.FC<TimelineProps> = ({
  segments,
  totalDuration,
  viewportStart,
  viewportDuration,
  onJumpTo
}) => {
  
  /**
   * Translates a mouse click coordinate into a file-absolute timestamp.
   */
  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const clickX = e.clientX - rect.left
    const percent = clickX / rect.width
    
    // Convert percentage of track to absolute file time
    let targetTime = percent * totalDuration
    
    // Constraint logic: Prevents the viewport from dragging past the file end,
    // which would cause the backend to return an empty array or index out of bounds.
    targetTime = Math.max(0, Math.min(targetTime, totalDuration - viewportDuration))
    onJumpTo(targetTime)
  }

  // Map absolute temporal bounds to percentage-based CSS positions
  const overlayLeft = (viewportStart / totalDuration) * 100
  const overlayWidth = (viewportDuration / totalDuration) * 100

  return (
    <div className="w-full flex flex-col gap-1 select-none">
      <div className="flex justify-between text-xs text-muted-foreground px-1">
        <span>0s</span>
        <span className="font-semibold text-primary">Artifact Minimap</span>
        <span>{totalDuration.toFixed(0)}s</span>
      </div>
      
      {/* The main interactive scrubbing track */}
      <div 
        className="w-full h-12 bg-muted/30 border border-border rounded relative cursor-pointer overflow-hidden shadow-inner group"
        onClick={handleTimelineClick}
      >
        {/* Render Segment blocks */}
        {segments.map((seg, i) => {
          // Normalize the segment window relative to the entire recording
          const leftP = (seg.start / totalDuration) * 100
          const widthP = ((seg.end - seg.start) / totalDuration) * 100
          
          let bgColor = 'bg-transparent'
          if (seg.severity === 'bad') bgColor = 'bg-red-500/60'
          else if (seg.severity === 'warning') bgColor = 'bg-yellow-500/40'
          
          return (
            <div
              key={i}
              className={`absolute top-0 bottom-0 ${bgColor} border-r border-background/20 transition-all hover:brightness-125`}
              style={{ left: `${leftP}%`, width: `${widthP}%` }}
              title={`Score: ${seg.quality_score} | Markers: ${seg.markers.map(m => m.type).join(',') || 'None'}`}
            >
              {/* Indicator pins for specific point-artifacts (e.g. sharp spikes) */}
              {seg.markers.length > 0 && (
                <div className="absolute -top-1 left-1/2 w-1 h-3 bg-foreground rounded-full transform -translate-x-1/2"></div>
              )}
            </div>
          )
        })}
        
        {/* The Viewport Overlay Box (the user's current camera positioning) */}
        <div 
          className="absolute top-0 bottom-0 bg-primary/20 border-x-2 border-primary shadow-[0_0_10px_rgba(var(--primary),0.5)] transition-all duration-300"
          style={{ left: `${overlayLeft}%`, width: `${overlayWidth}%` }}
        />
        
        {/* Hover scrub indicator (Visual polish for interaction) */}
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-200">
           <div className="w-full h-full bg-gradient-to-t from-background/20 to-transparent"></div>
        </div>
      </div>
    </div>
  )
}

export default ArtifactTimeline
