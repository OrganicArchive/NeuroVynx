import numpy as np
import mne
from app.eeg.quality.engine import compute_segment_quality

def scan_session_timeline(
    file_path: str,
    total_duration: float,
    window: float = 10.0,
    step: float = 5.0,
    apply_notch: bool = True,
    apply_bandpass: bool = True
):
    """
    Scans the EDF file lazily across sliding windows to generate a high-level timeline of artifacts.
    """
    raw = mne.io.read_raw_edf(file_path, preload=False, verbose=False)
    
    # CLEANUP: Strip trailing dots often found in standardized EDF exports
    raw.rename_channels(lambda ch: ch.strip('.'))
    
    sfreq = raw.info['sfreq']
    
    segments = []
    
    # Iterate across the duration
    start_t = 0.0
    while start_t + window <= total_duration:
        start_samp = int(start_t * sfreq)
        stop_samp = int((start_t + window) * sfreq)
        
        # We only strictly load the tiny window required
        raw_slice = raw.copy().crop(tmin=start_samp/sfreq, tmax=stop_samp/sfreq).load_data()
        
        if apply_notch:
            raw_slice.notch_filter(freqs=50.0, verbose=False)
        if apply_bandpass:
            raw_slice.filter(l_freq=1.0, h_freq=45.0, verbose=False)
            
        data_uv = raw_slice.get_data() * 1e6
        
        # Calculate heuristics without needing the full ML feature wrapper
        qual = compute_segment_quality(data_uv, raw_slice.ch_names, sfreq)
        
        score = qual["overall_quality_score"]
        severity = "good"
        if score < 50:
            severity = "bad"
        elif score < 80:
            severity = "warning"
            
        # Parse warnings back into clean marker structs
        markers = []
        for ch, info in qual["per_channel_status"].items():
            if info["status"] != "good":
                # Find exactly which rule tripped to create standard tags
                str_warns = " ".join(info["warnings"]).lower()
                
                m_type = "unknown"
                if "flatline" in str_warns: m_type = "flatline"
                elif "clipping" in str_warns: m_type = "clipping"
                elif "blink" in str_warns: m_type = "blink_suspected"
                elif "variance" in str_warns: m_type = "high_noise"
                
                # Check if we already registered this marker type to group channels
                found = False
                for m in markers:
                    if m["type"] == m_type:
                        m["channels"].append(ch)
                        found = True
                        break
                if not found:
                    markers.append({
                        "type": m_type,
                        "channels": [ch]
                    })
        
        segments.append({
            "start": start_t,
            "end": start_t + window,
            "quality_score": score,
            "severity": severity,
            "markers": markers
        })
        
        start_t += step
        
    return {
        "session_duration": total_duration,
        "window_size": window,
        "step_size": step,
        "segments": segments
    }
