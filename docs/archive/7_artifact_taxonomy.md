# Artifact Taxonomy

This document lists the artifacts the application is engineered to detect, their typical signatures, and the logic used to flag them. 

## 1. Eye Blink (Ocular Artifact)
- **Morphology**: Large amplitude, low frequency (< 5Hz) positive peak in frontal channels, typically lasting 200-400ms.
- **Main Channels Affected**: Fp1, Fp2, F7, F8.
- **Detection Strategy**: 
  - Heuristic: High amplitude threshold (>70 µV deviation from moving average) focused heavily in anterior electrodes, symmetrical.
  - Model: A lightweight Random Forest or CNN trained on short frontal epochs.
- **Mitigation Options**: Epoch rejection, ICA blink component removal.

## 2. Horizontal Eye Movement (Saccade)
- **Morphology**: Step-like voltage change, with opposite polarities between left and right frontal/temporal channels. (e.g. F7 goes negative, F8 goes positive).
- **Main Channels Affected**: F7, F8.
- **Detection Strategy**: Calculate the negative correlation (covariance) between F7 and F8; step-edge detection.
- **Mitigation Options**: Epoch rejection, ICA.

## 3. Jaw / Facial Muscle Activity (EMG Artifact)
- **Morphology**: High frequency bursts (typically > 20 Hz, bleeding into Beta/Gamma bands), high amplitude spiking.
- **Main Channels Affected**: T3/T7, T4/T8, F7, F8.
- **Detection Strategy**: Compute high-frequency band power (25-45 Hz); if it spikes 3+ standard deviations above the running baseline, flag as EMG.
- **Mitigation Options**: Interpolate affected channels (if localized) or Reject Epoch. Filter is often ineffective because it overlaps brain beta/gamma.

## 4. Head/Body Motion & Cable Sway
- **Morphology**: Massive, abrupt baseline drift, large slow waves (sweating), or multi-channel chaotic high-amplitude noise.
- **Main Channels Affected**: Global, or clustered on loose wires. 
- **Detection Strategy**: Global variance thresholding. Checking for simultaneous saturation (clipping) across multiple electrodes.
- **Mitigation Options**: Absolute data rejection. This data is usually unrecoverable.

## 5. Line Noise
- **Morphology**: Perfect sharp sine wave at 50Hz or 60Hz.
- **Main Channels Affected**: Any channel with high impedance.
- **Detection Strategy**: FFT analysis. Extract power within a narrow 49-51 Hz bin and compare to adjacent bins. If ratio > threshold, flag.
- **Mitigation Options**: Notch filter. 

## 6. Loose / High Impedance Electrode
- **Morphology**: Popping, drifting, random walk signals, 0 variance (flatline).
- **Main Channels Affected**: Individual.
- **Detection Strategy**: Check variance. Too low = flatline. Too high + random walk = loose.
- **Mitigation Options**: Channel interpolation.
