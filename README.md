# telegram-emoji-maker

This Python application converts GIF files into WebM format for compact, transparent animations, optimized for small file sizes. The output is configured for 100x100 pixel resolution, a maximum file size of 63 KB, and a maximum duration of 2.95 seconds, using VP9 encoding with alpha channel support for transparency.
Features

Converts GIF animations to WebM format with transparency.
Automatically crops transparent borders and resizes frames to 100x100 pixels.
Enforces a 63 KB file size limit through iterative compression (CRF adjustments).
Supports variable frame rates based on input GIF duration and frame count, up to 2.95 seconds.
User-friendly Tkinter GUI for selecting input GIF and output WebM file paths.

Prerequisites

Python 3.x: Ensure Python 3.6 or higher is installed.
FFmpeg: Required for video conversion. Download from ffmpeg.org or install via a package manager (e.g., choco install ffmpeg on Windows, sudo apt install ffmpeg on Ubuntu).
Add FFmpeg to your system's PATH environment variable.


Python Libraries: Install required libraries listed in requirements.txt.

Installation

Clone or download this repository to your local machine.
Install the required Python libraries:pip install -r requirements.txt


Ensure FFmpeg is installed and accessible in your system's PATH:
On Windows, run ffmpeg -version in a command prompt to verify.
On Linux/macOS, use ffmpeg -version in a terminal.



Usage

Run the script:python webm_animated_emoji_maker_telegram.py


The GUI will open:
Click "Browse" next to "Select Input GIF" to choose a GIF file.
Click "Browse" next to "Save WebM As" to specify the output WebM file path.
Click "Convert" to process the GIF and generate a WebM animation.


Monitor the status label for progress updates (e.g., "Processing frames...", "Conversion complete!").
If the output exceeds 63 KB, the script will retry with higher compression and display a warning if the limit cannot be met.

Notes

The input GIF should have transparency (alpha channel) for best results, as the script preserves transparency in the WebM output.
The output is tailored for 100x100 pixels and a 63 KB limit, suitable for compact animations (e.g., emoji-like stickers).
If conversion fails, check the error messages in the GUI for details (e.g., missing FFmpeg, invalid GIF).
The script creates a temporary directory for PNG frames, which is automatically deleted after conversion.

Troubleshooting

FFmpeg not found: Ensure FFmpeg is installed and added to your PATH. Verify by running ffmpeg -version.
Output file too large: The script automatically adjusts compression. If the file still exceeds 63 KB, try a simpler GIF with fewer frames or less complex visuals.
Invalid GIF: Ensure the input GIF is valid and contains animation frames.

License
This project is licensed under the MIT License. See the LICENSE file for details (if included).
Acknowledgments

Built with Python, Pillow, and FFmpeg.
Designed for creating compact WebM animations with transparency.
