/**
 * EegCanvasViewer Component
 * =========================
 * A high-performance signal visualization engine optimized for morphology inspection.
 * 
 * Visualization Philosophy:
 * - Direct-to-Canvas: Maps raw voltage deflections directly to pixel offsets 
 *   using HTML5 Canvas, bypassing expensive DOM-based charting overhead.
 * - LCD Morphology Accuracy: Implements Device Pixel Ratio (DPR) scaling to 
 *   ensure single-pixel trace clarity on high-density research monitors.
 * - Quality-Aware Coloring: Dynamically highlights trace segments based on 
 *   real-time heuristic quality scores (SNR) to guide the researcher's focus.
 */

import React, { useEffect, useRef } from 'react'

interface EegCanvasViewerProps {
  /** Raw EEG data matrix: [channels][samples] */
  data: number[][] 
  /** Ordered list of electrode labels */
  channels: string[]
  /** Biological sampling frequency of the source file */
  sampleRate: number
  /** User-controlled magnification of signal amplitude (Gain) */
  verticalScaleFactor?: number
  /** User-controlled spacing between channel rows */
  spacingFactor?: number
  /** Results from the quality engine to drive trace coloring */
  qualityData?: Record<string, { status: string }>
}

const EegCanvasViewer: React.FC<EegCanvasViewerProps> = ({ 
  data, 
  channels, 
  sampleRate,
  verticalScaleFactor = 1.0,
  spacingFactor = 1.0,
  qualityData
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // --- DATA INTEGRITY CHECKS ---
    if (data.length === 0 || !data[0] || data[0].length === 0) return
    const numSamples = data[0].length
    if (!sampleRate || sampleRate <= 0) return
    const durationSeconds = numSamples / sampleRate
    if (!isFinite(durationSeconds) || durationSeconds <= 0) return

    // --- DPI SCALING (CRITICAL FOR LCD ACCURACY) ---
    // High-resolution displays (Retina/4K) require scaling the drawing 
    // surface to match physical pixels. Without this, lines appear blurry.
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    const numChannels = data.length
    const baseRowHeight = 40 // Calibrated minimum row height for morphology inspection
    const rowHeight = baseRowHeight * spacingFactor // Now decoupled from gain
    
    // Dynamic Height calculation: instead of fitting to container, we grow to fit the channels.
    // The parent container in SessionViewer will handle the scrolling.
    const calculatedHeight = numChannels * rowHeight
    
    // Resize the canvas to fit the dynamic height
    canvas.width = rect.width * dpr
    canvas.height = calculatedHeight * dpr
    canvas.style.height = `${calculatedHeight}px`
    ctx.scale(dpr, dpr)
    
    const width = rect.width
    const height = calculatedHeight
    
    // Use a deep charcoal background (Zinc-950 equivalent) for medical legibility
    ctx.fillStyle = '#09090b' 
    ctx.fillRect(0, 0, width, height)

    // Draw 1-second vertical grid lines (Isolated background layer)
    ctx.save()
    ctx.beginPath()
    ctx.strokeStyle = '#111114' // Exceptionally muted gray
    ctx.lineWidth = 1
    for (let s = 1; s < Math.floor(durationSeconds); s++) {
      const x = (s / durationSeconds) * width
      ctx.moveTo(x, 0)
      ctx.lineTo(x, height)
    }
    ctx.stroke()
    ctx.restore()

    // Fine-tuned trace stroke for high visibility - reduced to 1.0 for morphology clarity
    ctx.lineWidth = 1.0
    ctx.lineJoin = 'round'

    // Functional Color Palette (Mapped to Signal Quality)
    // Tuned for better research contrast: Green is less neon, Warn/Bad are high-contrast.
    const defaultTraceColor = '#34d399' // Emerald-400 (Muted Research Green)
    const warningTraceColor = '#facc15' // Yellow-400 (Alert)
    const badTraceColor = '#f87171'     // Red-400 (Urgent)
    const inactiveTraceColor = '#3f3f46' // Zinc-700
    const labelColor = '#71717a'        // Zinc-500 labels

    // --- MAIN RENDERING LOOP ---
    for (let c = 0; c < numChannels; c++) {
      const channelData = data[c]
      if (!channelData) continue

      // Calculate vertical offset with optional spacing expansion
      // We center each trace in its row, but allow rowHeight to be influenced by the container
      const yOffset = c * rowHeight + (rowHeight / 2)
      const chName = channels[c] || `CH${c+1}`
      
      const qStatus = qualityData ? qualityData[chName]?.status : 'good'
      const chType = qualityData ? (qualityData[chName] as any)?.type : 'EEG'
      
      // Visual Severity Mapping (Context-Aware Backgrounds)
      if (chType !== 'MARKER') {
        if (qStatus === 'inactive') {
          ctx.fillStyle = 'rgba(63, 63, 70, 0.05)' // Muted Inactive
          ctx.fillRect(0, c * rowHeight, width, rowHeight)
        } else if (chType === 'EEG' && qStatus === 'bad') {
          ctx.fillStyle = 'rgba(248, 113, 113, 0.12)' // honest Red Alert
          ctx.fillRect(0, c * rowHeight, width, rowHeight)
        } else if (chType === 'EOG' && (qStatus === 'bad' || qStatus === 'warning')) {
          ctx.fillStyle = 'rgba(250, 204, 21, 0.08)' // Amber Warning (Physiological Context)
          ctx.fillRect(0, c * rowHeight, width, rowHeight)
        } else if (qStatus === 'warning' || qStatus === 'bad') {
          ctx.fillStyle = qStatus === 'bad' ? 'rgba(248, 113, 113, 0.08)' : 'rgba(250, 204, 21, 0.06)'
          ctx.fillRect(0, c * rowHeight, width, rowHeight)
        }
      }

      // Draw faint baseline horizontal guide
      ctx.beginPath()
      ctx.strokeStyle = '#18181b' 
      ctx.lineWidth = 0.5
      ctx.moveTo(0, yOffset)
      ctx.lineTo(width, yOffset)
      ctx.stroke()
      
      // Render electrode label (Compact Inter)
      ctx.fillStyle = labelColor
      ctx.font = 'bold 9px Inter, ui-sans-serif'
      ctx.fillText(chName, 8, yOffset - 10)

      // --- SIGNAL TRACE DRAWING ---
      ctx.beginPath()
      ctx.lineWidth = 1.0 // Reset to calibrated width
      
      if (qStatus === 'inactive') ctx.strokeStyle = inactiveTraceColor
      else if (qStatus === 'bad') ctx.strokeStyle = badTraceColor
      else if (qStatus === 'warning') ctx.strokeStyle = warningTraceColor
      else ctx.strokeStyle = defaultTraceColor
      
      const traceLen = Math.min(numSamples, channelData.length)
      for (let i = 0; i < traceLen; i++) {
        const x = (i / numSamples) * width
        // Apply vertical gain
        const y = yOffset - (channelData[i] * verticalScaleFactor)
        
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.stroke()
    }
  }, [data, channels, verticalScaleFactor, spacingFactor, qualityData, sampleRate])

  return (
    <div className="w-full h-full relative bg-background border border-border rounded-md overflow-hidden">
      <canvas 
        ref={canvasRef} 
        className="w-full block" 
        style={{ cursor: 'crosshair' }}
      />
    </div>
  )
}

export default EegCanvasViewer
