from moviepy import VideoFileClip
import os

captures_dir = r"[LOCAL_PATH]"
output_dir = r"[LOCAL_PATH]"

# Map of manually cropped source files to clean gallery filenames
video_map = {
    "Real-Time EEG Platform MVP - edf file upload.mp4": "data_upload.gif",
    "Real-Time EEG Platform MVP - Open session in viewer.mp4": "session_init.gif",
    "Real-Time EEG Platform MVP - Channel over view.mp4": "signal_viewer.gif",
    "Real-Time EEG Platform MVP - Top bar over view.mp4": "researcher_controls.gif",
    "Real-Time EEG Platform MVP - Interpret over view.mp4": "interpretive_logic.gif",
    "Real-Time EEG Platform MVP - Topomap showcase.mp4": "spatial_topography.gif",
    "Real-Time EEG Platform MVP - Plugin manger view.mp4": "plugin_system.gif",
    "Real-Time EEG Platform MVP - Features over view .mp4": "advanced_features.gif"
}

def convert_video(src_name, dest_name):
    src_path = os.path.join(captures_dir, src_name)
    dest_path = os.path.join(output_dir, dest_name)
    
    if not os.path.exists(src_path):
        print(f"Skipping: {src_name} (Not found)")
        return

    print(f"\n--- Converting Refined Feature: {src_name} ---")
    clip = VideoFileClip(src_path)
    
    # Optimization: 800px width, 10fps
    # No additional cropping needed as user handled it manually.
    print(f"Resizing and writing GIF...")
    clip_resized = clip.resized(width=800).with_fps(10)
    clip_resized.write_gif(dest_path)
    
    clip.close()
    clip_resized.close()
    print(f"Complete: {dest_name} ({os.path.getsize(dest_path) / (1024*1024):.2f} MB)")

# Run batch
os.makedirs(output_dir, exist_ok=True)
for src, dest in video_map.items():
    convert_video(src, dest)

print("\nFinal feature gallery conversion complete!")
