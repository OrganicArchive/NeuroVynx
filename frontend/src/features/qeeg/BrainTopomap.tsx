import React, { useRef, useEffect } from 'react';

/**
 * BrainTopomap: 2D Scalp Visualization Component
 * --------------------------------------------
 * Renders EEG scalp maps using HTML5 Canvas.
 * 
 * MODES:
 * 1. 'relative_power' (Default): Uses a Standard Sequential Scale (Indig-Emerald-Rose).
 *    Visualizes local spatial contrast of band power percentages.
 * 
 * 2. 'normative_z_map': Uses a Diverging Signed Scale (Blue-White-Red).
 *    Visualizes deviations from a reference population (Z-scores).
 *    Zero (0.0) is anchored as Neutral White.
 */
interface BrainTopomapProps {
  gridData: number[][]; // 64x64 matrix of interpolated values
  electrodes: any[];    // List of sensors with {name, x, y, value}
  trustLevel: 'trusted' | 'borderline' | 'unavailable';
  metricLabel: string;
  vMin: number;
  vMax: number;
  isLowVariance: boolean;
  mapType?: 'relative_power' | 'normative_z_map';
  symmetricLimit?: number; // Used for normative scaling [-limit, +limit]
}

const BrainTopomap: React.FC<BrainTopomapProps> = ({ 
  gridData, electrodes, trustLevel, metricLabel, 
  vMin, vMax, isLowVariance,
  mapType = 'relative_power',
  symmetricLimit = 2.0
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoverElectrode, setHoverElectrode] = React.useState<any>(null);
  const [viewMode, setViewMode] = React.useState<'combined' | 'heatmap' | 'electrodes'>('combined');

  useEffect(() => {
    if (!canvasRef.current || !gridData.length) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const size = canvas.width;
    const centerX = size / 2;
    const centerY = size / 2;
    const radius = size * 0.45;

    ctx.clearRect(0, 0, size, size);

    // 1. Draw Heatmap (if enabled)
    if (viewMode !== 'electrodes') {
      const gridSize = gridData.length;
      const buffer = document.createElement('canvas');
      buffer.width = gridSize;
      buffer.height = gridSize;
      const bCtx = buffer.getContext('2d');
      
      if (bCtx) {
        const imgData = bCtx.createImageData(gridSize, gridSize);
        
        for (let y = 0; y < gridSize; y++) {
          for (let x = 0; x < gridSize; x++) {
            const rawVal = gridData[y][x];
            let normVal: number;
            
             if (mapType === 'normative_z_map') {
              // Center at 0.5 (White), range is [-limit, +limit]
              normVal = 0.5 + (rawVal / (2 * symmetricLimit));
            } else {
              // Standard normalization [0.0, 1.0]
              const range = vMax - vMin;
              normVal = range > 0.0001 ? (rawVal - vMin) / range : 0.5;
            }

            const color = mapType === 'normative_z_map' 
              ? getNormativeColor(normVal) 
              : getColorForValue(normVal);
            
            const idx = (y * gridSize + x) * 4;
            imgData.data[idx] = color.r;
            imgData.data[idx + 1] = color.g;
            imgData.data[idx + 2] = color.b;

            // GEOMETRIC MASKING: Decouple alpha channel from raw value magnitude.
            // This ensures Z=0 or Z<0 remain visible as long as they are inside the scalp.
            const gx = -1.1 + (x * 2.2 / (gridSize - 1));
            const gy = -1.1 + (y * 2.2 / (gridSize - 1));
            const isInside = (gx * gx + gy * gy) <= 1.05;
            imgData.data[idx + 3] = isInside ? 255 : 0;
          }
        }
        bCtx.putImageData(imgData, 0, 0);

        ctx.save();
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.clip();
        ctx.imageSmoothingEnabled = true;
        ctx.drawImage(buffer, 0, 0, size, size);
        ctx.restore();
      }
    }

    // 2. Draw Scalp Outlines & Markers
    drawScalpOutline(ctx, centerX, centerY, radius, trustLevel);

    // 3. Draw Electrodes (with value mapping in debug mode)
    drawElectrodes(ctx, electrodes, centerX, centerY, radius, trustLevel, viewMode !== 'heatmap');

  }, [gridData, electrodes, trustLevel, vMin, vMax, viewMode]);

  const getColorForValue = (val: number) => {
    const v = Math.max(0, Math.min(1, val));
    if (v < 0.25) return lerpColor({ r: 40, g: 40, b: 80 }, { r: 0, g: 150, b: 255 }, v / 0.25);
    if (v < 0.5) return lerpColor({ r: 0, g: 150, b: 255 }, { r: 16, g: 185, b: 129 }, (v - 0.25) / 0.25);
    if (v < 0.75) return lerpColor({ r: 16, g: 185, b: 129 }, { r: 245, g: 158, b: 11 }, (v - 0.5) / 0.25);
    return lerpColor({ r: 245, g: 158, b: 11 }, { r: 244, g: 63, b: 94 }, (v - 0.75) / 0.25);
  };

  const getNormativeColor = (val: number) => {
    const v = Math.max(0, Math.min(1, val));
    // Blue (Reduced) -> White (Near Reference) -> Red (Elevated)
    if (v < 0.5) {
       return lerpColor({ r: 30, g: 60, b: 200 }, { r: 255, g: 255, b: 255 }, v * 2);
    }
    return lerpColor({ r: 255, g: 255, b: 255 }, { r: 220, g: 38, b: 38 }, (v - 0.5) * 2);
  };

  const lerpColor = (c1: any, c2: any, f: number) => ({
    r: Math.round(c1.r + (c2.r - c1.r) * f),
    g: Math.round(c1.g + (c2.g - c1.g) * f),
    b: Math.round(c1.b + (c2.b - c1.b) * f)
  });

  const drawScalpOutline = (ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number, trust: string) => {
    ctx.strokeStyle = trust === 'borderline' ? 'rgba(234, 179, 8, 0.4)' : 'rgba(255, 255, 255, 0.2)';
    ctx.lineWidth = 1.5;
    
    // Circle & Nose
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx - 10, cy - r); ctx.lineTo(cx, cy - r - 15); ctx.lineTo(cx + 10, cy - r); ctx.stroke();
    
    // Ears
    ctx.beginPath(); ctx.arc(cx - r - 5, cy, 10, -Math.PI / 2, Math.PI / 2, true); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx + r + 5, cy, 10, -Math.PI / 2, Math.PI / 2); ctx.stroke();

    // ORIENTATION MARKERS
    ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.font = 'bold 9px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('N', cx, cy - r + 15);
    ctx.fillText('L', cx - r + 15, cy + 3);
    ctx.fillText('R', cx + r - 15, cy + 3);
  };

  const drawElectrodes = (ctx: CanvasRenderingContext2D, electrodes: any[], cx: number, cy: number, r: number, trust: string, showColors: boolean) => {
    electrodes.forEach(e => {
      const ex = cx + (e.x * r * 0.9);
      const ey = cy - (e.y * r * 0.9);
      
      const rawVal = e.value[metricLabel.toLowerCase()];
      let normVal: number;
      if (mapType === 'normative_z_map') {
        normVal = 0.5 + (rawVal / (2 * symmetricLimit));
      } else {
        const range = vMax - vMin;
        normVal = range > 0.0001 ? (rawVal - vMin) / range : 0.5;
      }
      
      const color = mapType === 'normative_z_map' 
        ? getNormativeColor(normVal) 
        : getColorForValue(normVal);

      // Dot
      ctx.beginPath();
      ctx.arc(ex, ey, 3.5, 0, Math.PI * 2);
      if (showColors) {
         ctx.fillStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
         ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
         ctx.lineWidth = 1;
         ctx.fill();
         ctx.stroke();
      } else {
         ctx.fillStyle = trust === 'borderline' ? 'rgba(234, 179, 8, 0.8)' : 'white';
         ctx.fill();
      }

      // Label
      ctx.fillStyle = 'rgba(255, 255, 100, 0.5)';
      ctx.font = '7px Inter';
      ctx.textAlign = 'center';
      ctx.fillText(e.name, ex, ey + 12);
    });
  };

  return (
    <div className="relative flex flex-col items-center gap-4 py-2 group">
      {/* Mode Toggle */}
      <div className="flex gap-1 bg-muted/20 p-1 rounded-md border border-border/20">
         {(['combined', 'heatmap', 'electrodes'] as const).map(m => (
            <button 
              key={m}
              onClick={() => setViewMode(m)}
              className={`text-[8px] px-2 py-0.5 rounded uppercase font-bold transition-all ${
                viewMode === m ? 'bg-primary text-primary-foreground shadow-lg' : 'text-muted-foreground hover:bg-muted/30'
              }`}
            >
               {m}
            </button>
         ))}
      </div>

      <div className={`relative p-4 bg-muted/10 rounded-full border border-border/20 shadow-inner transition-opacity ${trustLevel === 'borderline' || isLowVariance ? 'opacity-80 saturate-[0.8]' : ''}`}>
        <canvas 
          ref={canvasRef} 
          width={280} 
          height={280}
          className="rounded-full cursor-crosshair"
          onMouseMove={(e) => {
             const rect = canvasRef.current?.getBoundingClientRect();
             if (!rect) return;
             const mouseX = e.clientX - rect.left;
             const mouseY = e.clientY - rect.top;
             const cx = 140, cy = 140, r = 140 * 0.45;
             const nearest = electrodes.find(elect => {
                const ex = cx + (elect.x * r * 0.9);
                const ey = cy - (elect.y * r * 0.9);
                const dist = Math.sqrt((ex - mouseX)**2 + (ey - mouseY)**2);
                return dist < 12;
             });
             setHoverElectrode(nearest || null);
          }}
          onMouseLeave={() => setHoverElectrode(null)}
        />
        
        {isLowVariance && !hoverElectrode && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
             <div className="bg-muted/80 text-muted-foreground text-[9px] font-bold px-4 py-2 rounded-full border border-border/40 backdrop-blur-md text-center max-w-[180px]">
                SPATIAL VARIATION LOW<br/>
                <span className="font-normal opacity-70">Uniform scalp distribution detected</span>
             </div>
          </div>
        )}

        {hoverElectrode && (
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
             <div className="bg-black/80 text-white text-[10px] font-mono p-3 rounded-lg border border-white/20 backdrop-blur-xl shadow-2xl flex flex-col gap-1 min-w-[100px]">
                <div className="flex justify-between border-b border-white/10 pb-1 mb-1">
                   <span className="font-bold text-primary">{hoverElectrode.name}</span>
                   <span className="opacity-60">Electrode</span>
                </div>
                <div className="flex justify-between">
                   <span className="opacity-60">{mapType === 'normative_z_map' ? 'Z-Score:' : 'Value:'}</span>
                   <span className="font-bold">
                     {mapType === 'normative_z_map' 
                       ? hoverElectrode.value[metricLabel.toLowerCase()].toFixed(2)
                       : (hoverElectrode.value[metricLabel.toLowerCase()] * 100).toFixed(1) + '%'
                     }
                   </span>
                </div>
                {mapType !== 'normative_z_map' && (
                  <div className="flex justify-between">
                    <span className="opacity-60">Norm:</span>
                    <span className="font-bold">{((hoverElectrode.value[metricLabel.toLowerCase()] - vMin) / (vMax - vMin + 0.0001) * 100).toFixed(0)}%</span>
                  </div>
                )}
             </div>
          </div>
        )}
      </div>
      
      <div className="flex flex-col items-center">
         <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
           {mapType === 'normative_z_map' ? 'Deviation from Reference' : `${metricLabel} Map`}
         </span>
         <div className="flex items-center gap-2 mt-1">
            <span className="text-[8px] text-muted-foreground font-mono">
              {mapType === 'normative_z_map' ? `-${symmetricLimit.toFixed(1)}` : `${(vMin * 100).toFixed(1)}%`}
            </span>
            <div className={`w-24 h-1.5 rounded-full shadow-sm ${
              mapType === 'normative_z_map' 
                ? 'bg-gradient-to-r from-blue-700 via-white to-red-600'
                : 'bg-gradient-to-r from-indigo-900 via-emerald-500 to-rose-500'
            }`} />
            <span className="text-[8px] text-muted-foreground font-mono">
              {mapType === 'normative_z_map' ? `+${symmetricLimit.toFixed(1)}` : `${(vMax * 100).toFixed(1)}%`}
            </span>
         </div>
         {mapType === 'normative_z_map' && (
            <div className="flex justify-between w-48 mt-1 text-[7px] text-muted-foreground font-bold uppercase tracking-tighter opacity-70">
               <span>Reduced</span>
               <span>Reference</span>
               <span>Elevated</span>
            </div>
         )}
      </div>
    </div>
  );
};

export default BrainTopomap;
