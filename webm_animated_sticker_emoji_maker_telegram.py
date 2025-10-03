import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageSequence
import subprocess
import os
import tempfile
import shutil

# Configuration
MAX_SIZE_KB_STICKER = 256
MAX_SIZE_KB_EMOJI = 64
MAX_DURATION_ANIMATED = 2.95  # seconds for animated GIFs
MAX_DURATION_STATIC = 2.0  # seconds for static images
STICKER_SIZE = 512  # One side must be 512 pixels
EMOJI_SIZE = (100, 100)  # Exactly 100x100 pixels
DEFAULT_FPS = 30  # Default frame rate for static images

class WebMStickerEmojiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Sticker & Emoji WebM Converter")
        self.root.geometry("500x400")
        self.root.configure(bg="#2c2f33")  # Dark theme background

        # Style configuration
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 10), padding=10)
        style.map("TButton", background=[("active", "#45a049")])
        style.configure("TLabel", font=("Arial", 10), background="#2c2f33", foreground="#ffffff")
        style.configure("TEntry", fieldbackground="#3a3f47", foreground="#ffffff")

        # Main frame
        main_frame = tk.Frame(root, bg="#2c2f33")
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Title
        tk.Label(main_frame, text="Telegram Sticker & Emoji Converter", font=("Arial", 16, "bold"), bg="#2c2f33", fg="#ffffff").pack(pady=10)
        tk.Label(main_frame, text="Create WebM stickers (512px side, ≤256KB) or emoji (100x100px, ≤64KB)", font=("Arial", 10), bg="#2c2f33", fg="#bbbbbb").pack(pady=5)

        # Input files
        tk.Label(main_frame, text="Select Input Images (GIF, PNG, JPEG):", bg="#2c2f33", fg="#ffffff").pack(pady=5)
        self.input_entry = ttk.Entry(main_frame, width=50)
        self.input_entry.pack(pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_input).pack(pady=5)

        # Output folder
        tk.Label(main_frame, text="Select Output Folder:", bg="#2c2f33", fg="#ffffff").pack(pady=5)
        self.output_entry = ttk.Entry(main_frame, width=50)
        self.output_entry.pack(pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output_folder).pack(pady=5)

        # Convert buttons
        ttk.Button(main_frame, text="Make Stickers (512px side)", command=lambda: self.convert(is_sticker=True), style="TButton").pack(pady=10)
        ttk.Button(main_frame, text="Make Emojis (100x100px)", command=lambda: self.convert(is_sticker=False), style="TButton").pack(pady=10)

        # Status label
        self.status_label = tk.Label(main_frame, text="", font=("Arial", 10), bg="#2c2f33", fg="#bbbbbb")
        self.status_label.pack(pady=5)

    def browse_input(self):
        files = filedialog.askopenfilenames(filetypes=[("Image files", "*.gif;*.png;*.jpg;*.jpeg")])
        if files:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, ";".join(files))
            self.status_label.config(text=f"{len(files)} input files selected")

    def browse_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)
            self.status_label.config(text="Output folder selected")

    def is_animated_gif(self, image_path):
        """Check if the input is an animated GIF."""
        try:
            with Image.open(image_path) as im:
                return im.is_animated if hasattr(im, "is_animated") else False
        except Exception:
            return False

    def get_duration(self, image_path, is_animated):
        """Calculate duration and frame durations for input image."""
        if is_animated:
            try:
                with Image.open(image_path) as im:
                    durations = [frame.info.get('duration', 100) / 1000 for frame in ImageSequence.Iterator(im)]
                total_duration = sum(durations)
                if total_duration > MAX_DURATION_ANIMATED:
                    # Speed up by scaling frame durations
                    speed_factor = total_duration / MAX_DURATION_ANIMATED
                    durations = [d / speed_factor for d in durations]
                    total_duration = MAX_DURATION_ANIMATED
                return total_duration, durations
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read GIF: {e}")
                return 0, []
        else:
            # For static images, calculate frame count to fill MAX_DURATION_STATIC
            frame_count = int(MAX_DURATION_STATIC * DEFAULT_FPS)
            frame_duration = MAX_DURATION_STATIC / frame_count
            return MAX_DURATION_STATIC, [frame_duration] * frame_count

    def resize_frame(self, frame, is_sticker=True):
        """Resize a single frame to Telegram sticker or emoji dimensions."""
        if frame.mode != "RGBA":
            frame = frame.convert("RGBA")
        
        if is_sticker:
            # Sticker: One side must be 512, other ≤ 512
            width, height = frame.size
            aspect_ratio = width / height
            if width >= height:
                target_width = STICKER_SIZE
                target_height = min(int(STICKER_SIZE / aspect_ratio), STICKER_SIZE)
            else:
                target_height = STICKER_SIZE
                target_width = min(int(STICKER_SIZE * aspect_ratio), STICKER_SIZE)
            target_size = (target_width, target_height)
        else:
            # Emoji: Exactly 100x100
            target_size = EMOJI_SIZE

        frame.thumbnail(target_size, Image.Resampling.LANCZOS)
        new_frame = Image.new("RGBA", target_size, (0, 0, 0, 0))
        offset = ((target_size[0] - frame.size[0]) // 2, (target_size[1] - frame.size[1]) // 2)
        new_frame.paste(frame, offset)
        return new_frame

    def create_webm(self, input_pattern, output_path, duration, frame_count, is_animated, is_sticker):
        """Convert image sequence to VP9 WebM with FFmpeg."""
        try:
            max_duration = MAX_DURATION_ANIMATED if is_animated else MAX_DURATION_STATIC
            max_size_kb = MAX_SIZE_KB_STICKER if is_sticker else MAX_SIZE_KB_EMOJI
            scale = "512:512" if is_sticker else "100:100"
            total_duration = min(duration, max_duration)
            fps = frame_count / total_duration
            speed_factor = duration / max_duration if duration > max_duration else 1.0
            setpts = f"setpts={1/speed_factor}*PTS"
            loop_filter = ",loop=-1" if is_animated else ""  # Loop animated GIFs

            crf = 30
            max_attempts = 5
            for attempt in range(max_attempts):
                cmd = [
                    "ffmpeg",
                    "-i", input_pattern,
                    "-c:v", "libvpx-vp9",
                    "-b:v", "0",
                    "-crf", str(crf),
                    "-vf", f"{setpts},fps={fps},scale={scale}:force_original_aspect_ratio=decrease,pad={scale}:(ow-iw)/2:(oh-ih)/2:color=black@0{loop_filter}",
                    "-an",  # No audio
                    "-y",  # Overwrite output
                    output_path
                ]
                self.status_label.config(text=f"Converting with CRF={crf}...")
                self.root.update()
                subprocess.run(cmd, check=True, capture_output=True)
                if os.path.getsize(output_path) / 1024 <= max_size_kb:
                    break
                crf += 5
                if attempt == max_attempts - 1:
                    messagebox.showwarning("Warning", f"WebM exceeds {max_size_kb} KB. Using highest compression.")
            self.status_label.config(text="Conversion complete!")
        except subprocess.CalledProcessError as e:
            self.status_label.config(text="Conversion failed")
            messagebox.showerror("Error", f"FFmpeg failed: {e.stderr.decode()}")
        except Exception as e:
            self.status_label.config(text="Conversion failed")
            messagebox.showerror("Error", f"Failed to create WebM: {e}")

    def convert(self, is_sticker=True):
        """Handle batch conversion process."""
        input_paths = self.input_entry.get().split(";")
        output_folder = self.output_entry.get()

        if not input_paths or not output_folder:
            self.status_label.config(text="Missing file paths or output folder")
            messagebox.showerror("Error", "Please specify both input files and output folder.")
            return

        valid_inputs = [path for path in input_paths if os.path.exists(path)]
        if not valid_inputs:
            self.status_label.config(text="No valid input files")
            messagebox.showerror("Error", "No valid input files found.")
            return

        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                self.status_label.config(text="Failed to create output folder")
                messagebox.showerror("Error", f"Failed to create output folder: {e}")
                return

        # Process each input file
        for input_path in valid_inputs:
            self.status_label.config(text=f"Processing {os.path.basename(input_path)}...")
            self.root.update()

            # Create temporary directory for PNG sequence
            temp_dir = tempfile.mkdtemp()
            try:
                # Check if input is an animated GIF
                is_animated = self.is_animated_gif(input_path)
                self.status_label.config(text=f"Processing frames for {os.path.basename(input_path)}...")
                self.root.update()

                # Process input image
                with Image.open(input_path) as im:
                    if is_animated:
                        frames = [frame.copy() for frame in ImageSequence.Iterator(im)]
                    else:
                        # For static images, duplicate frame to fill MAX_DURATION_STATIC
                        frame_count = int(MAX_DURATION_STATIC * DEFAULT_FPS)
                        frames = [im.copy() for _ in range(frame_count)]

                # Resize frames (no cropping)
                processed_frames = []
                for frame in frames:
                    resized = self.resize_frame(frame, is_sticker)
                    processed_frames.append(resized)

                # Save frames as PNG sequence
                temp_files = []
                for i, frame in enumerate(processed_frames):
                    temp_file = os.path.join(temp_dir, f"frame_{i:04d}.png")
                    frame.save(temp_file, format="PNG")
                    temp_files.append(temp_file)

                # Get duration
                total_duration, frame_durations = self.get_duration(input_path, is_animated)
                frame_count = len(frames)

                # Create WebM
                base_name = os.path.splitext(os.path.basename(input_path))[0]
                output_path = os.path.join(output_folder, f"{base_name}.webm")
                input_pattern = os.path.join(temp_dir, "frame_%04d.png")
                self.create_webm(input_pattern, output_path, total_duration, frame_count, is_animated, is_sticker)

            except Exception as e:
                self.status_label.config(text=f"Processing failed for {os.path.basename(input_path)}")
                messagebox.showerror("Error", f"Processing failed for {os.path.basename(input_path)}: {e}")
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        self.status_label.config(text="Batch conversion complete!")

if __name__ == "__main__":
    root = tk.Tk()
    app = WebMStickerEmojiApp(root)
    root.mainloop()