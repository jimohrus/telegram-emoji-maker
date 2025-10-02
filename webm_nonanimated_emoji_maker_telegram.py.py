import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk, UnidentifiedImageError
import os

# Inline the core functions
import numpy as np
import imageio

def is_animated_gif(image_path):
    """
    Check if the input is an animated GIF.
    """
    if not image_path.lower().endswith('.gif'):
        return False
    try:
        with Image.open(image_path) as img:
            return 'duration' in img.info or img.is_animated
    except Exception:
        return False

def is_animated_webp(image_path):
    """
    Check if the input is an animated WebP.
    """
    if not image_path.lower().endswith('.webp'):
        return False
    try:
        import imageio.v3 as iio
        reader = iio.imread(image_path)
        return len(reader) > 1 if hasattr(reader, '__len__') else False
    except Exception:
        return False

def is_image_file(image_path):
    """
    Check if the file is an image format supported by PIL.
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    ext = os.path.splitext(image_path)[1].lower()
    return ext in image_extensions

def has_alpha(image_path):
    """
    Check if the image has an alpha channel.
    """
    try:
        with Image.open(image_path) as img:
            return img.mode in ('RGBA', 'LA') or (hasattr(img, 'info') and 'transparency' in img.info)
    except Exception:
        return False

def resize_image(image_path):
    """
    Resize the image to exactly 100x100 pixels, preserving alpha channel if present.
    Returns a resized PIL Image and its dimensions (100, 100).
    """
    try:
        with Image.open(image_path) as img:
            mode = 'RGBA' if has_alpha(image_path) else 'RGB'
            img = img.convert(mode)
            resized_img = img.resize((100, 100), Image.Resampling.LANCZOS)
            print(f"Resized to 100x100, mode: {mode} (input was {img.size[0]}x{img.size[1]})")
            return resized_img, 100, 100
    except UnidentifiedImageError:
        import imageio.v3 as iio
        img = iio.imread(image_path)
        if len(img.shape) == 3 and img.shape[2] == 4:
            mode = 'RGBA'
        else:
            mode = 'RGB'
            if len(img.shape) == 3 and img.shape[2] == 4:
                img = img[:, :, :3]  # Remove alpha if not needed
        pil_img = Image.fromarray(img, mode=mode)
        resized_img = pil_img.resize((100, 100), Image.Resampling.LANCZOS)
        print(f"Resized to 100x100, mode: {mode} (WebP fallback)")
        return resized_img, 100, 100
    except Exception as e:
        raise ValueError(f"Error resizing image: {e}")

def create_webm_video(resized_img, output_path, duration=2.0, fps=30, strict=False):
    """
    Create a WebM video from the resized image (static loop), preserving alpha.
    Optimized for Telegram emoji: CRF 45 (or 50 if strict), low bitrate, muted.
    """
    img_array = np.array(resized_img)
    num_frames = int(duration * fps)
    frames = [img_array] * num_frames
    
    writer_params = {
        'format': 'FFMPEG',
        'pixelformat': 'yuva420p' if resized_img.mode == 'RGBA' else 'yuv420p',
        'ffmpeg_params': [
            '-crf', '50' if strict else '45',
            '-c:v', 'libvpx-vp9',
            '-b:v', '20k' if strict else '24k',
            '-vf', 'scale=100:100',
            '-b:a', '64k',
            '-c:a', 'libopus',
            '-strict', '-2',
            '-y'
        ]
    }
    
    with imageio.get_writer(output_path, fps=fps, **writer_params) as writer:
        for frame in frames:
            writer.append_data(frame)
    
    file_size = os.path.getsize(output_path) / 1024  # KB
    alpha_status = "with alpha" if resized_img.mode == 'RGBA' else "no alpha"
    print(f"Created WebM video: {output_path} ({duration}s at {fps} FPS, muted, {file_size:.2f} KB, {alpha_status})")
    return file_size

def create_webm_from_video(input_path, output_path, max_duration=2.99, strict=False):
    """
    Create muted WebM from input video: extract frames up to max_duration, resize to 100x100, preserve alpha.
    """
    try:
        reader = imageio.get_reader(input_path)
        meta = reader.get_meta_data()
        orig_duration = meta.get('duration', 5.0)
        fps = meta.get('fps', 30)
        
        # Cap duration
        duration = min(orig_duration, max_duration)
        num_frames_to_process = int(duration * fps)
        
        def resize_frame(frame):
            mode = 'RGBA' if len(frame.shape) == 3 and frame.shape[2] == 4 else 'RGB'
            if mode == 'RGB' and len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = frame[:, :, :3]
            pil_img = Image.fromarray(frame, mode=mode)
            return np.array(pil_img.resize((100, 100), Image.Resampling.LANCZOS))
        
        first_frame = next(reader)
        has_alpha_channel = len(first_frame.shape) == 3 and first_frame.shape[2] == 4
        reader.close()
        reader = imageio.get_reader(input_path)  # Reopen reader
        
        writer_params = {
            'format': 'FFMPEG',
            'pixelformat': 'yuva420p' if has_alpha_channel else 'yuv420p',
            'ffmpeg_params': [
                '-crf', '50' if strict else '45',
                '-c:v', 'libvpx-vp9',
                '-b:v', '20k' if strict else '24k',
                '-vf', 'scale=100:100',
                '-an',
                '-strict', '-2',
                '-y'
            ]
        }
        
        frame_count = 0
        with imageio.get_writer(output_path, fps=fps, **writer_params) as writer:
            for frame in reader:
                if frame_count >= num_frames_to_process:
                    break
                resized_frame = resize_frame(frame)
                writer.append_data(resized_frame)
                frame_count += 1
        
        file_size = os.path.getsize(output_path) / 1024  # KB
        alpha_status = "with alpha" if has_alpha_channel else "no alpha"
        print(f"Created muted WebM from video: {output_path} ({duration}s at {fps} FPS, {file_size:.2f} KB, {alpha_status})")
        return duration, fps, file_size
    except Exception as e:
        raise ValueError(f"Error processing video: {e}")

def process_animated_image(image_path, output_path, max_duration=2.99, user_fps=30, strict=False):
    """
    Process animated GIF or WebP: extract frames up to max_duration, resize to 100x100, preserve alpha.
    """
    try:
        reader = imageio.get_reader(image_path)
        meta = reader.get_meta_data()
        orig_duration = meta.get('duration', 5.0)
        fps = meta.get('fps', user_fps)
        
        # Cap duration
        duration = min(orig_duration, max_duration)
        num_frames_to_process = int(duration * fps)
        
        def resize_frame(frame):
            mode = 'RGBA' if len(frame.shape) == 3 and frame.shape[2] == 4 else 'RGB'
            if mode == 'RGB' and len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = frame[:, :, :3]
            pil_img = Image.fromarray(frame, mode=mode)
            return np.array(pil_img.resize((100, 100), Image.Resampling.LANCZOS))
        
        first_frame = next(reader)
        has_alpha_channel = len(first_frame.shape) == 3 and first_frame.shape[2] == 4
        reader.close()
        reader = imageio.get_reader(image_path)  # Reopen reader
        
        writer_params = {
            'format': 'FFMPEG',
            'pixelformat': 'yuva420p' if has_alpha_channel else 'yuv420p',
            'ffmpeg_params': [
                '-crf', '50' if strict else '45',
                '-c:v', 'libvpx-vp9',
                '-b:v', '20k' if strict else '24k',
                '-vf', 'scale=100:100',
                '-b:a', '64k',
                '-c:a', 'libopus',
                '-strict', '-2',
                '-y'
            ]
        }
        
        frame_count = 0
        with imageio.get_writer(output_path, fps=fps, **writer_params) as writer:
            for frame in reader:
                if frame_count >= num_frames_to_process:
                    break
                resized_frame = resize_frame(frame)
                writer.append_data(resized_frame)
                frame_count += 1
        
        file_size = os.path.getsize(output_path) / 1024  # KB
        alpha_status = "with alpha" if has_alpha_channel else "no alpha"
        print(f"Created muted WebM from animated image: {output_path} ({duration}s at {fps} FPS, {file_size:.2f} KB, {alpha_status})")
        return file_size
    except Exception as e:
        raise ValueError(f"Error processing animated image: {e}")

class EmojiToWebMGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Emoji WebM Converter")
        self.root.geometry("600x500")
        
        # Variables
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar(value="emoji.webm")
        self.duration = tk.DoubleVar(value=2.99)
        self.fps = tk.IntVar(value=30)
        self.resized_dims = tk.StringVar(value="No file selected")
        
        self.setup_ui()
        
    def setup_ui(self):
        tk.Label(self.root, text="Input Media:").pack(pady=5)
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=5)
        tk.Entry(input_frame, textvariable=self.input_path, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="Browse", command=self.browse_input).pack(side=tk.LEFT, padx=5)
        
        tk.Label(self.root, text="Output WebM:").pack(pady=5)
        output_frame = tk.Frame(self.root)
        output_frame.pack(pady=5)
        tk.Entry(output_frame, textvariable=self.output_path, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(output_frame, text="Browse", command=self.browse_output).pack(side=tk.LEFT, padx=5)
        
        settings_frame = tk.LabelFrame(self.root, text="Settings", padx=10, pady=10)
        settings_frame.pack(pady=10, fill=tk.X, padx=20)
        
        tk.Label(settings_frame, text="Duration (seconds, max 2.99 for animations, 2.0 for static):").grid(row=0, column=0, sticky=tk.W)
        tk.Entry(settings_frame, textvariable=self.duration, width=10).grid(row=0, column=1)
        
        tk.Label(settings_frame, text="FPS:").grid(row=1, column=0, sticky=tk.W)
        tk.Entry(settings_frame, textvariable=self.fps, width=10).grid(row=1, column=1)
        
        tk.Label(settings_frame, text="Note: Outputs are 100x100px, muted, ≤64KB, with alpha channel if present.", fg="red").grid(row=2, column=0, columnspan=2, sticky=tk.W)
        
        tk.Label(self.root, text="Preview (Resized Dims):").pack(pady=5)
        tk.Label(self.root, textvariable=self.resized_dims, fg="blue").pack()
        
        tk.Button(self.root, text="Convert to WebM Emoji", command=self.convert, bg="green", fg="white", font=("Arial", 12, "bold")).pack(pady=20)
        
        tk.Label(self.root, text="Status Log:").pack(pady=5)
        self.log = scrolledtext.ScrolledText(self.root, height=8, width=70)
        self.log.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
    
    def log_message(self, message):
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.root.update()
    
    def browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select Input Media",
            filetypes=[
                ("Media files", "*.jpg *.jpeg *.png *.gif *.bmp *.tiff *.webp *.mp4 *.mov *.avi *.mkv *.wmv *.flv"),
                ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.tiff *.webp"),
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.input_path.set(filename)
            try:
                if is_image_file(filename):
                    resized_img, w, h = resize_image(filename)
                    alpha_status = "with alpha" if resized_img.mode == 'RGBA' else "no alpha"
                    self.resized_dims.set(f"100x100 (after resize, {alpha_status})")
                    anim_type = ""
                    if filename.lower().endswith('.gif'):
                        anim_type = " (animated GIF)" if is_animated_gif(filename) else " (static GIF)"
                    elif filename.lower().endswith('.webp'):
                        anim_type = " (animated WebP)" if is_animated_webp(filename) else " (static WebP)"
                    else:
                        anim_type = " (static image)"
                    self.log_message(f"Selected: {os.path.basename(filename)} - Preview: 100x100 {alpha_status}{anim_type}")
                    resized_img.close()
                else:
                    import imageio.v3 as iio
                    first_frame = iio.imread(filename)[0]
                    alpha_status = "with alpha" if len(first_frame.shape) == 3 and first_frame.shape[2] == 4 else "no alpha"
                    pil_img = Image.fromarray(first_frame, mode='RGBA' if alpha_status == "with alpha" else 'RGB')
                    pil_img = pil_img.resize((100, 100), Image.Resampling.LANCZOS)
                    self.resized_dims.set(f"100x100 (video frame after resize, {alpha_status})")
                    self.log_message(f"Selected video: {os.path.basename(filename)} - Preview frame resized to 100x100 (will be muted, {alpha_status})")
            except Exception as e:
                messagebox.showerror("Error", f"Invalid file: {e}")
                self.resized_dims.set("Error loading file")
    
    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save WebM As",
            defaultextension=".webm",
            filetypes=[("WebM files", "*.webm"), ("All files", "*.*")]
        )
        if filename:
            self.output_path.set(filename)
    
    def convert(self):
        input_file = self.input_path.get().strip()
        output_file = self.output_path.get().strip()
        
        if not input_file:
            messagebox.showerror("Error", "Please select an input file.")
            return
        if not output_file:
            messagebox.showerror("Error", "Please specify an output file.")
            return
        
        if not os.path.exists(input_file):
            messagebox.showerror("Error", f"Input file not found: {input_file}")
            return
        
        try:
            self.log_message("Starting conversion (output will be muted, 100x100px, alpha preserved)...")
            self.root.update()
            
            user_fps = self.fps.get()
            user_duration = self.duration.get()
            static_max = 2.0
            anim_max = 2.99
            telegram_size_limit = 64  # KB
            
            is_image = is_image_file(input_file)
            is_animated = False
            final_duration = user_duration
            final_fps = user_fps
            anim_status = ""
            file_size = 0
            strict = False
            
            if is_image:
                if input_file.lower().endswith(('.gif', '.webp')):
                    is_animated = is_animated_gif(input_file) if input_file.lower().endswith('.gif') else is_animated_webp(input_file)
                    if is_animated:
                        anim_status = " (animated image)"
                        if final_duration > anim_max:
                            self.log_message(f"Animated image detected: Capping duration to {anim_max} seconds (was {final_duration})")
                            final_duration = anim_max
                        file_size = process_animated_image(input_file, output_file, anim_max, final_fps)
                    else:
                        anim_status = " (static image)"
                        if final_duration > static_max:
                            self.log_message(f"Static image detected: Capping duration to {static_max} seconds (was {final_duration})")
                            final_duration = static_max
                        resized_img, w, h = resize_image(input_file)
                        self.resized_dims.set(f"100x100 (processing, {resized_img.mode})")
                        self.log_message(f"Resized to 100x100, mode: {resized_img.mode}")
                        file_size = create_webm_video(resized_img, output_file, final_duration, final_fps)
                        resized_img.close()
                else:
                    anim_status = " (static image)"
                    if final_duration > static_max:
                        self.log_message(f"Static image detected: Capping duration to {static_max} seconds (was {final_duration})")
                        final_duration = static_max
                    resized_img, w, h = resize_image(input_file)
                    self.resized_dims.set(f"100x100 (processing, {resized_img.mode})")
                    self.log_message(f"Resized to 100x100, mode: {resized_img.mode}")
                    file_size = create_webm_video(resized_img, output_file, final_duration, final_fps)
                    resized_img.close()
            else:
                anim_status = " (video, muted)"
                if user_duration > anim_max:
                    self.log_message(f"Video duration setting ignored; using input duration capped to {anim_max}s")
                final_duration, final_fps, file_size = create_webm_from_video(input_file, output_file, anim_max)
                self.resized_dims.set(f"100x100 (video frames)")
                self.log_message(f"Video processed: {final_duration}s at {final_fps} FPS{anim_status}")
            
            # Check file size
            if file_size > telegram_size_limit:
                self.log_message(f"WARNING: File size {file_size:.2f} KB exceeds Telegram's 64 KB emoji limit.")
                retry = messagebox.askyesno("Warning", f"Output is {file_size:.2f} KB, too large for Telegram emoji (max 64 KB). Retry with stricter compression?")
                if retry:
                    self.log_message("Retrying with stricter compression...")
                    strict = True
                    if is_image and is_animated:
                        file_size = process_animated_image(input_file, output_file, anim_max, final_fps, strict=True)
                    elif is_image:
                        resized_img, w, h = resize_image(input_file)
                        file_size = create_webm_video(resized_img, output_file, final_duration, final_fps, strict=True)
                        resized_img.close()
                    else:
                        final_duration, final_fps, file_size = create_webm_from_video(input_file, output_file, anim_max, strict=True)
                    if file_size > telegram_size_limit:
                        self.log_message(f"STILL TOO LARGE: {file_size:.2f} KB. Try simpler image, shorter duration, or lower FPS.")
                        messagebox.showerror("Error", f"Retry failed: {file_size:.2f} KB exceeds 64 KB limit. Use simpler input or lower FPS.")
                    else:
                        self.log_message(f"Retry successful: {file_size:.2f} KB")
                        messagebox.showinfo("Success", f"Retry complete! Duration: {final_duration}s{anim_status} (muted, {file_size:.2f} KB)")
                else:
                    messagebox.showwarning("Warning", f"Output is {file_size:.2f} KB, too large for Telegram emoji. Try simpler input or lower FPS.")
            
            if file_size <= telegram_size_limit:
                self.log_message(f"Success! Saved to: {output_file} ({final_duration}s duration{anim_status}, {file_size:.2f} KB)")
                messagebox.showinfo("Success", f"Conversion complete! Duration: {final_duration}s{anim_status} (muted, {file_size:.2f} KB)")

        except Exception as e:
            error_msg = f"Conversion failed: {e}"
            self.log_message(error_msg)
            messagebox.showerror("Error", error_msg)

def main():
    root = tk.Tk()
    app = EmojiToWebMGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()