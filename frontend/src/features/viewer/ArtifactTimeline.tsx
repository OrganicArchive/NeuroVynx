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
   * Translates a mouse click coordinate into a file-absolute timestamp,
   * snapping to the 5s discrete tiles for clinical alignment.
   */
  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const clickX = e.clientX - rect.left
    const percent = clickX / rect.width
    
    // Convert to absolute time and snap to nearest 5s boundary
    const tileWidth = 5.0
    let targetTime = Math.round((percent * totalDuration) / tileWidth) * tileWidth
    
    // Constraint logic
    targetTime = Math.max(0, Math.min(targetTime, totalDuration - viewportDuration))
    onJumpTo(targetTime)
  }

  // Snap UI visualization to the closest 5s grid boundaries for cleaner presentation
  const tileWidth = 5.0
  const snappedStart = Math.round(viewportStart / tileWidth) * tileWidth
  const snappedDuration = Math.round(viewportDuration / tileWidth) * tileWidth

  const overlayLeft = (snappedStart / totalDuration) * 100
  const overlayWidth = (snappedDuration / totalDuration) * 100

  return (
    <div className="w-full flex flex-col gap-1 select-none">
      <div className="flex justify-between text-xs text-muted-foreground px-1">
        <span>0s</span>
        <span className="font-semibold text-primary">Artifact Minimap</span>
        <span>{totalDuration.toFixed(0)}s</span>
      </div>
      
      {/* The main interactive scrubbing track */}
      <div 
        className="w-full h-12 bg-white/5 border border-white/10 rounded relative cursor-pointer overflow-hidden shadow-inner group transition-colors hover:border-white/20"
        onClick={handleTimelineClick}
      >
        {/* Render Segment blocks */}
        {(!segments || segments.length === 0) ? (
          <div className="absolute inset-0 flex items-center justify-center opacity-30">
            <div className="flex gap-1 animate-pulse">
               {[...Array(20)].map((_, i) => (
                  <div key={i} className="w-4 h-full bg-white/10 rounded-sm"></div>
               ))}
            </div>
          </div>
        ) : (
          segments.map((seg, i) => {
            // Coordinate math: Tiles are now discrete (e.g. 0-5s, 5-10s)
            // Use precise start/end mapping to percentage space
            const leftP = (seg.start / totalDuration) * 100
            const widthP = ((seg.end - seg.start) / totalDuration) * 100
            
            let bgColor = 'bg-green-500/20'
            if (seg.severity === 'bad') bgColor = 'bg-red-500/60'
            else if (seg.severity === 'warning') bgColor = 'bg-yellow-500/40'
            
            return (
              <div
                key={i}
                className={`absolute top-0 bottom-0 ${bgColor} border-r border-background/20 transition-all hover:brightness-125`}
                style={{ left: `${leftP}%`, width: `${widthP}%` }}
                title={`Score: ${seg.quality_score} | Markers: ${seg.markers.map(m => m.type).join(',') || 'None'}`}
              >
                {/* Discrete Marker Rendering (Centered in tile) */}
                {seg.markers.length > 0 && (
                  <div className="absolute top-0 bottom-0 left-1/2 w-[1px] bg-white/40 transform -translate-x-1/2"></div>
                )}
              </div>
            )
          })
        )}
        
        {/* The Viewport Overlay Box (the user's current camera positioning) */}
        {/* Using sharp borders and primary color for high-visibility snapping */}
        <div 
          className="absolute top-0 bottom-0 bg-primary/20 border-x-2 border-primary transition-all duration-300 pointer-events-none"
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
