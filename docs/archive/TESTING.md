# NeuroVynx Testing & QA

Because NeuroVynx directly interfaces with heavy standardized datasets, testing the I/O threshold of the application is a massive priority. Please review the following Quality Assurance protocols before modifying core engines.

## 1. File Ingestion Handling

*   **Valid Uploads**: Ensure the system instantly accepts standard `10-20` mapping `.edf` and `.bdf` systems. 
*   **Invalid Files**: Uploading an `.mp4` or a corrupted text file simply returns a `400 Bad Request: Invalid EDF formatting` gracefully via MNE's header parsing rather than crashing the Python worker.
*   **Large File Behavior**: Because the system loads arrays lazily via `preload=False`, ingesting a massive 12+ hour sleep recording should take identical exact time to upload compared to a 10-second file.

## 2. DSP & Signal Accuracy

*   **Filter Accuracy**: Validate the `notch_filter(50.0)` toggling visibly removes high-frequency jagged oscillation from European/American lines.
*   **Quality Heuristics**: If you modify `app/eeg/quality/engine.py`, ensure the flatline threshold (`< 0.05 uV^2`) is not accidentally clipping normal, high-performing occipital channels.

## 3. UI Resiliency

*   **Backend Offline**: If the FastAPI server drops, the React interface will surface a standard `Disconnected | 500 Network Error` boundary.
*   **Timeline Precision**: Ensure the timeline minimap mathematical offset perfectly centers the 10-second slice. Dragging the timeline all the way to 100% bounds should gracefully lock to `Total_Duration - 10s` to prevent MNE array indexing exceptions out-of-bounds.
*   **Empty Baseline States**: If a user attempts to generate a comparison on a fresh DB instance, the UI simply gracefully says `"No baseline configured for deviation."` instead of throwing a massive React Null pointer exception.
