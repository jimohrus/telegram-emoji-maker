import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageSequence
import subprocess
import os
import numpy as np
import tempfile
import shutil

# Configuration
MAX_SIZE_KB = 63
MAX_DURATION = 2.95  # seconds
TARGET_SIZE = (100, 100)

class WebMConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WebM Animation Converter")
        self.root.geometry("500x350")
        self.root.configure(bg="#2c2f33")  # Dark theme background

        # Style configuration for modern look
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 10), padding=10)
        style.map("TButton", background=[("active", "#45a049")])
        style.configure("TLabel", font=("Arial", 10), background="#2c2f33", foreground="#ffffff")
        style.configure("TEntry", fieldbackground="#3a3f47", foreground="#ffffff")

        # Main frame
        main_frame = tk.Frame(root, bg="#2c2f33")
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Title
        tk.Label(main_frame, text="GIF to WebM Converter", font=("Arial", 16, "bold"), bg="#2c2f33", fg="#ffffff").pack(pady=10)
        tk.Label(main_frame, text="Create compact, transparent WebM animations", font=("Arial", 10), bg="#2c2f33", fg="#bbbbbb").pack(pady=5)

        # Input file
        tk.Label(main_frame, text="Select Input GIF:", bg="#2c2f33", fg="#ffffff").pack(pady=5)
        self.input_entry = ttk.Entry(main_frame, width=50)
        self.input_entry.pack(pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_input).pack(pady=5)

        # Output WebM
        tk.Label(main_frame, text="Save WebM As:", bg="#2c2f33", fg="#ffffff").pack(pady=5)
        self.webm_entry = ttk.Entry(main_frame, width=50)
        self.webm_entry.pack(pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_webm).pack(pady=5)

        # Convert button
        ttk.Button(main_frame, text="Convert", command=self.convert, style="TButton").pack(pady=20)

        # Status label
        self.status_label = tk.Label(main_frame, text="", font=("Arial", 10), bg="#2c2f33", fg="#bbbbbb")
        self.status_label.pack(pady=5)

    def browse_input(self):
        file = filedialog.askopenfilename(filetypes=[("GIF files", "*.gif")])
        if file:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, file)
            self.status_label.config(text="Input selected")

    def browse_webm(self):
        file = filedialog.asksaveasfilename(defaultextension=".webm", filetypes=[("WebM files", "*.webm")])
        if file:
            self.webm_entry.delete(0, tk.END)
            self.webm_entry.insert(0, file)
            self.status_label.config(text="Output path selected")

    def get_duration(self, gif_path):
        """Calculate duration of GIF in seconds."""
        try:
            with Image.open(gif_path) as im:
                durations = [frame.info.get('duration', 100) / 1000 for frame in ImageSequence.Iterator(im)]
            return sum(durations), durations
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read GIF: {e}")
            return 0, []

    def crop_transparency(self, frame):
        """Crop a single frame to remove transparent borders."""
        frame = frame.convert("RGBA")
        data = np.array(frame)
        non_transparent = data[:, :, 3] > 0
        if non_transparent.any():
            rows = np.any(non_transparent, axis=1)
            cols = np.any(non_transparent, axis=0)
            row_min, row_max = np.where(rows)[0][[0, -1]]
            col_min, col_max = np.where(cols)[0][[0, -1]]
            return frame.crop((col_min, row_min, col_max + 1, row_max + 1))
        return frame

    def resize_frame(self, frame, size):
        """Resize a single frame to fit within target size."""
        frame.thumbnail(size, Image.Resampling.LANCZOS)
        new_frame = Image.new("RGBA", size, (0, 0, 0, 0))
        offset = ((size[0] - frame.size[0]) // 2, (size[1] - frame.size[1]) // 2)
        new_frame.paste(frame, offset)
        return new_frame

    def create_webm(self, input_path, output_path, duration, frame_count):
        """Convert GIF to VP9 WebM with FFmpeg."""
        try:
            # Adjust duration if necessary
            total_duration = duration
            fps = frame_count / min(total_duration, MAX_DURATION)
            if total_duration > MAX_DURATION:
                setpts = f"setpts={total_duration/MAX_DURATION}*PTS"
            else:
                setpts = "setpts=PTS"

            # FFmpeg command for VP9 WebM with transparency
            crf = 30  # Start with lower CRF for better quality
            max_attempts = 3
            for attempt in range(max_attempts):
                cmd = [
                    "ffmpeg",
                    "-i", input_path,
                    "-c:v", "libvpx-vp9",
                    "-b:v", "0",
                    "-crf", str(crf),
                    "-vf", f"{setpts},fps={fps},scale=100:100:force_original_aspect_ratio=decrease,pad=100:100:(ow-iw)/2:(oh-ih)/2:color=black@0",
                    "-an",  # No audio
                    "-y",  # Overwrite output
                    output_path
                ]
                self.status_label.config(text=f"Converting with CRF={crf}...")
                self.root.update()
                subprocess.run(cmd, check=True, capture_output=True)
                if os.path.getsize(output_path) / 1024 <= MAX_SIZE_KB:
                    break
                crf += 5  # Increase CRF to reduce size
                if attempt == max_attempts - 1:
                    messagebox.showwarning("Warning", "WebM exceeds 63 KB. Using highest compression.")
            self.status_label.config(text="Conversion complete!")
        except subprocess.CalledProcessError as e:
            self.status_label.config(text="Conversion failed")
            messagebox.showerror("Error", f"FFmpeg failed: {e.stderr.decode()}")
        except Exception as e:
            self.status_label.config(text="Conversion failed")
            messagebox.showerror("Error", f"Failed to create WebM: {e}")

    def convert(self):
        """Handle conversion process."""
        input_path = self.input_entry.get()
        webm_path = self.webm_entry.get()

        if not input_path or not webm_path:
            self.status_label.config(text="Missing file paths")
            messagebox.showerror("Error", "Please specify both input and output file paths.")
            return

        if not os.path.exists(input_path):
            self.status_label.config(text="Input file not found")
            messagebox.showerror("Error", "Input file does not exist.")
            return

        # Create temporary directory for PNG sequence
        temp_dir = tempfile.mkdtemp()
        try:
            # Process GIF frames
            self.status_label.config(text="Processing frames...")
            self.root.update()
            with Image.open(input_path) as im:
                frames = [frame.copy() for frame in ImageSequence.Iterator(im)]
                frame_durations = [frame.info.get('duration', 100) / 1000 for frame in frames]

            # Crop and resize frames
            processed_frames = []
            for frame in frames:
                cropped = self.crop_transparency(frame)
                resized = self.resize_frame(cropped, TARGET_SIZE)
                processed_frames.append(resized)

            # Save frames as PNG sequence
            temp_files = []
            for i, frame in enumerate(processed_frames):
                temp_file = os.path.join(temp_dir, f"frame_{i:04d}.png")
                frame.save(temp_file, format="PNG")
                temp_files.append(temp_file)

            # Get duration and adjust
            total_duration = sum(frame_durations)
            frame_count = len(frames)

            # Create WebM from PNG sequence
            self.create_webm(os.path.join(temp_dir, "frame_%04d.png"), webm_path, total_duration, frame_count)

        except Exception as e:
            self.status_label.config(text="Processing failed")
            messagebox.showerror("Error", f"Processing failed: {e}")
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = WebMConverterApp(root)
    root.mainloop()