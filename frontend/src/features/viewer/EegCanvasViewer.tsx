/**
 * EegCanvasViewer Component
 * =========================
 * 
 * A high-performance signal visualization component that utilizes the 
 * native HTML5 Canvas API for low-latency, recursive rendering of 
 * multi-channel EEG traces.
 * 
 * Designed to handle high-density data (256Hz+ sampling) by mapping 
 * voltage deflections directly to coordinate offsets, bypassing the 
 * overhead of heavy charting libraries.
 */

import React, { useEffect, useRef } from 'react'

interface EegCanvasViewerProps {
  /** Raw EEG data matrix: [channels][samples] */
  data: number[][] 
  /** Ordered list of electrode labels */
  channels: string[]
  /** Biological sampling frequency of the source file */
  sampleRate: number
  /** User-controlled magnification of signal amplitude */
  verticalScaleFactor?: number
  /** Results from the quality engine to drive trace coloring */
  qualityData?: Record<string, { status: string }>
}

const EegCanvasViewer: React.FC<EegCanvasViewerProps> = ({ 
  data, 
  channels, 
  sampleRate,
  verticalScaleFactor = 1.0,
  qualityData
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // --- DPI SCALING (CRITICAL FOR LCD ACCURACY) ---
    // High-resolution displays (Retina/4K) require scaling the drawing 
    // surface to match physical pixels. Without this, lines appear blurry.
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    const width = rect.width
    const height = rect.height
    
    // Use a deep charcoal background (Zinc-950 equivalent) for medical legibility
    ctx.fillStyle = '#09090b' 
    ctx.fillRect(0, 0, width, height)

    const numChannels = data.length
    const rowHeight = height / numChannels
    const numSamples = data[0].length

    // Fine-tuned trace stroke for high visibility
    ctx.lineWidth = 1.5
    ctx.lineJoin = 'round'

    // Functional Color Palette (Mapped to Signal Quality)
    const defaultTraceColor = '#10b981' // Green (Clean signal)
    const warningTraceColor = '#eab308' // Yellow (Transient artifacts)
    const badTraceColor = '#ef4444'     // Red (Lead off / clipping)
    const labelColor = '#a1a1aa'        // Muted labels

    // --- MAIN RENDERING LOOP ---
    // We iterate over each channel and compute its vertical offset.
    for (let c = 0; c < numChannels; c++) {
      const channelData = data[c]
      const yOffset = c * rowHeight + (rowHeight / 2) // baseline Y coordinate
      const chName = channels[c]
      
      const qStatus = qualityData ? qualityData[chName]?.status : 'good'
      
      // Draw background alerts if quality is compromised (Visual alerting)
      if (qStatus === 'bad') {
        ctx.fillStyle = 'rgba(239, 68, 68, 0.1)' // faint red zone
        ctx.fillRect(0, c * rowHeight, width, rowHeight)
      } else if (qStatus === 'warning') {
        ctx.fillStyle = 'rgba(234, 179, 8, 0.05)' // faint yellow zone
        ctx.fillRect(0, c * rowHeight, width, rowHeight)
      }

      // Draw faint baseline grid line
      ctx.beginPath()
      ctx.strokeStyle = '#27272a' 
      ctx.moveTo(0, yOffset)
      ctx.lineTo(width, yOffset)
      ctx.stroke()
      
      // Render electrode label
      ctx.fillStyle = labelColor
      ctx.font = '12px Inter, sans-serif'
      ctx.fillText(chName, 10, yOffset - 10)

      // --- SIGNAL TRACE DRAWING ---
      ctx.beginPath()
      if (qStatus === 'bad') ctx.strokeStyle = badTraceColor
      else if (qStatus === 'warning') ctx.strokeStyle = warningTraceColor
      else ctx.strokeStyle = defaultTraceColor
      
      for (let i = 0; i < numSamples; i++) {
        // Horizontal mapping: time -> pixels
        const x = (i / numSamples) * width
        
        // Vertical mapping: voltage -> pixels
        // Subtraction (yOffset - ...) is necessary because Canvas Y=0 is the TOP of the frame.
        const y = yOffset - (channelData[i] * verticalScaleFactor)
        
        if (i === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      }
      ctx.stroke()
    }
  }, [data, channels, verticalScaleFactor, qualityData])

  return (
    <div className="w-full h-full relative bg-background border border-border rounded-md overflow-hidden">
      <canvas 
        ref={canvasRef} 
        className="w-full h-full block" 
        style={{ cursor: 'crosshair' }}
      />
    </div>
  )
}

export default EegCanvasViewer
