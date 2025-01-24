import cv2
import tkinter as tk
from tkinter import Scale, StringVar, Button, Checkbutton, BooleanVar, messagebox
import chuniio
from PIL import Image, ImageTk
import numpy as np
import keyboard  # Requires `keyboard` library
import json

zones = [
    {"x": 300, "y": 100, "width": 50, "height": 50},
    {"x": 300, "y": 200, "width": 50, "height": 50},
    {"x": 300, "y": 300, "width": 50, "height": 50},
    {"x": 300, "y": 400, "width": 50, "height": 50},
    {"x": 300, "y": 500, "width": 50, "height": 50},
    {"x": 300, "y": 600, "width": 50, "height": 50},
]

_UMIGIRI_32_AIRZONE_LAYOUT = {
    0: "o",
    1: "0",
    2: "p",
    3: "l",
    4: ",",
    5: ".",
}

base_positions = [{"x": zone["x"], "y": zone["y"]} for zone in zones]
zone_color_state = []
CONFIG_FILE = "config.json"
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
ZONE_TRIGGERED_STATE = [False] * len(zones)


def get_avg_brightness(frame, zone):
    x, y, w, h = zone["x"], zone["y"], zone["width"], zone["height"]
    roi = frame[y : y + h, x : x + w]
    if roi.size == 0:
        return 0
    return np.mean(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY))


def get_available_cameras():
    print("Now testing to see which cameras are available... (disregard the errors here)")
    available_cameras = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
    return available_cameras


def calculate_preview_size(width, height, max_height=720):
    """Calculate preview dimensions maintaining aspect ratio"""
    if height <= max_height:
        return width, height

    aspect_ratio = width / height
    new_height = max_height
    new_width = int(aspect_ratio * new_height)
    return new_width, new_height


def setup_gui(
    camera_width: int, camera_height: int, preview_width: int, preview_height: int
) -> tk.Tk:
    root = tk.Tk()
    root.title("chuni-hands-evolved")
    root.attributes("-topmost", True)

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    window_width = min(int(screen_width * 0.8), preview_width + 40)
    window_height = min(int(screen_height * 0.8), preview_height + 300)

    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    style = {
        "bg": "#f0f0f0",
        "padding": 10,
        "button_bg": "#4a90e2",
        "button_fg": "white",
        "frame_bg": "#ffffff",
        "label_font": ("Arial", 10),
        "button_font": ("Arial", 10, "bold"),
    }

    root.configure(bg=style["bg"])

    main_container = tk.Frame(
        root, bg=style["bg"], padx=style["padding"], pady=style["padding"]
    )
    main_container.pack(
        fill="both", expand=True, padx=style["padding"], pady=style["padding"]
    )

    # Video canvas
    video_frame = tk.Frame(main_container, bg=style["frame_bg"], relief="ridge", bd=2)
    video_frame.pack(fill="both", expand=True, pady=(0, style["padding"]))

    video_canvas = tk.Canvas(video_frame, width=preview_width, height=preview_height)
    video_canvas.pack(fill="both", expand=True)

    # Camera selection
    camera_frame = tk.Frame(
        main_container, bg=style["frame_bg"], relief="ridge", bd=2, padx=10, pady=10
    )
    camera_frame.pack(fill="x", pady=(0, style["padding"]))

    tk.Label(
        camera_frame,
        text="Camera Number:",
        font=style["label_font"],
        bg=style["frame_bg"],
    ).pack(side="left")

    available_cameras = get_available_cameras()
    if not available_cameras:
        print("No cameras found!")
        available_cameras = [0]

    camera_var = StringVar()
    camera_var.set(
        str(
            current_camera_index
            if current_camera_index in available_cameras
            else available_cameras[0]
        )
    )
    camera_dropdown = tk.OptionMenu(camera_frame, camera_var, *available_cameras)
    camera_dropdown.configure(width=10)
    camera_dropdown.pack(side="left", padx=(10, 0))

    tk.Label(
        camera_frame,
        text="Update Rate (ms):",
        font=style["label_font"],
        bg=style["frame_bg"],
    ).pack(side="left")

    update_rate = tk.StringVar(value="5")
    update_rate_spinbox = tk.Spinbox(
        camera_frame,
        from_=1,
        to=100,
        textvariable=update_rate,
        width=5,
    )
    update_rate_spinbox.pack(side="left", padx=5)

    tk.Label(
        camera_frame,
        text="You should set the update rate to something like 100 while editing for a smoother experience, then set it back to 5 for normal use.",
        font=style["label_font"],
        bg=style["frame_bg"],
    ).pack(side="top", pady=(0, style["padding"]))

    controls_frame = tk.Frame(
        main_container, bg=style["frame_bg"], relief="ridge", bd=2, padx=10, pady=10
    )
    controls_frame.pack(fill="x", pady=(0, style["padding"]))

    inputs_frame = tk.Frame(controls_frame, bg=style["frame_bg"])
    inputs_frame.pack(fill="x")

    x_frame = tk.Frame(inputs_frame, bg=style["frame_bg"])
    x_frame.pack(fill="x", pady=(0, 5))
    tk.Label(
        x_frame,
        text="X Position:",
        font=style["label_font"],
        bg=style["frame_bg"],
        width=15,
    ).pack(side="left")

    x_var = tk.StringVar(value="0")
    x_spinbox = tk.Spinbox(
        x_frame,
        from_=-500,
        to=1280,
        textvariable=x_var,
        increment=10,
        width=10,
        command=lambda: update_position("x"),
    )
    x_spinbox.pack(side="left", padx=5)

    x_slider = Scale(
        x_frame,
        from_=-500,
        to=1280,
        orient="horizontal",
        length=400,
        showvalue=0,
        command=lambda v: x_var.set(str(int(float(v)))),
    )
    x_slider.pack(side="left", fill="x", expand=True, padx=5)

    y_frame = tk.Frame(inputs_frame, bg=style["frame_bg"])
    y_frame.pack(fill="x", pady=(0, 5))
    tk.Label(
        y_frame,
        text="Y Position:",
        font=style["label_font"],
        bg=style["frame_bg"],
        width=15,
    ).pack(side="left")

    y_var = tk.StringVar(value="0")
    y_spinbox = tk.Spinbox(
        y_frame,
        from_=-200,
        to=720,
        textvariable=y_var,
        increment=10,
        width=10,
        command=lambda: update_position("y"),
    )
    y_spinbox.pack(side="left", padx=5)

    y_slider = Scale(
        y_frame,
        from_=-200,
        to=720,
        orient="horizontal",
        length=400,
        showvalue=0,
        command=lambda v: y_var.set(str(int(float(v)))),
    )
    y_slider.pack(side="left", fill="x", expand=True, padx=5)

    # Spacing controls
    spacing_frame = tk.Frame(inputs_frame, bg=style["frame_bg"])
    spacing_frame.pack(fill="x")
    tk.Label(
        spacing_frame,
        text="Sensor Spacing:",
        font=style["label_font"],
        bg=style["frame_bg"],
        width=15,
    ).pack(side="left")

    spacing_var = tk.StringVar(value="100")
    spacing_spinbox = tk.Spinbox(
        spacing_frame,
        from_=10,
        to=300,
        textvariable=spacing_var,
        increment=5,
        width=10,
        command=lambda: update_position("spacing"),
    )
    spacing_spinbox.pack(side="left", padx=5)

    spacing_slider = Scale(
        spacing_frame,
        from_=10,
        to=300,
        orient="horizontal",
        length=400,
        showvalue=0,
        command=lambda v: spacing_var.set(str(int(float(v)))),
    )
    spacing_slider.pack(side="left", fill="x", expand=True, padx=5)

    width_frame = tk.Frame(inputs_frame, bg=style["frame_bg"])
    width_frame.pack(fill="x")
    tk.Label(
        width_frame,
        text="Sensor Width:",
        font=style["label_font"],
        bg=style["frame_bg"],
        width=15,
    ).pack(side="left")

    width_var = tk.StringVar(value="50")
    width_spinbox = tk.Spinbox(
        width_frame,
        from_=10,
        to=1000,
        textvariable=width_var,
        increment=5,
        width=10,
        command=lambda: update_width(),
    )
    width_spinbox.pack(side="left", padx=5)

    def update_width():
        try:
            value = int(width_var.get())
            if 10 <= value <= 1000:
                for zone in zones:
                    zone["width"] = value
        except ValueError:
            pass

    def update_position(type):
        try:
            if type == "x":
                value = int(x_var.get())
                if -500 <= value <= 1280:
                    x_slider.set(value)
            elif type == "y":
                value = int(y_var.get())
                if -200 <= value <= 720:
                    y_slider.set(value)
            elif type == "spacing":
                value = int(spacing_var.get())
                if 10 <= value <= 300:
                    spacing_slider.set(value)
        except ValueError:
            pass

    def on_mousewheel(event, spinbox):
        if event.delta > 0:
            spinbox.invoke("buttonup")
        else:
            spinbox.invoke("buttondown")

    x_spinbox.bind("<MouseWheel>", lambda e: on_mousewheel(e, x_spinbox))
    y_spinbox.bind("<MouseWheel>", lambda e: on_mousewheel(e, y_spinbox))
    spacing_spinbox.bind("<MouseWheel>", lambda e: on_mousewheel(e, spacing_spinbox))
    width_spinbox.bind("<MouseWheel>", lambda e: on_mousewheel(e, width_spinbox))

    buttons_frame = tk.Frame(
        main_container, bg=style["frame_bg"], relief="ridge", bd=2, padx=10, pady=10
    )
    buttons_frame.pack(fill="x")

    def recalibrate():
        ret, frame = cap.read()
        if ret:
            calibrate(frame)
            print("Recalibration complete.")
        else:
            print("Error: Could not capture frame for recalibration.")

    def save_config():
        config = {
            "x_offset": x_slider.get(),
            "y_offset": y_slider.get(),
            "spacing": spacing_slider.get(),
            "width": int(width_var.get()),
            "camera_index": current_camera_index,
            "chuniio_enabled": chuniio_enabled.get(),
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        messagebox.showinfo("Config", "Configuration saved successfully.")

    button_kwargs = {
        "bg": style["button_bg"],
        "fg": style["button_fg"],
        "font": style["button_font"],
        "relief": "flat",
        "padx": 20,
        "pady": 5,
    }

    calibration_button = Button(
        buttons_frame, text="Recalibrate", command=recalibrate, **button_kwargs
    )
    calibration_button.pack(side="left", padx=5)

    save_button = Button(
        buttons_frame, text="Save Config", command=save_config, **button_kwargs
    )
    save_button.pack(side="left", padx=5)

    chuniio_enabled = BooleanVar(value=True)
    chuniio_button = Checkbutton(
        buttons_frame,
        text="Brokenithm Evolved chuniio",
        variable=chuniio_enabled,
        font=style["button_font"],
        relief="flat",
        padx=20,
        pady=5,
        bg=style["frame_bg"],
    )
    chuniio_button.pack(side="right", padx=5)

    keystrokes_enabled = BooleanVar(value=False)
    keystroke_button = Button(
        buttons_frame,
        text="⌨ Keystrokes: OFF",
        command=lambda: toggle_keystrokes(),
        **button_kwargs,
    )
    keystroke_button.pack(side="right", padx=5)

    def toggle_keystrokes():
        current = keystrokes_enabled.get()
        keystrokes_enabled.set(not current)
        keystroke_button.config(
            text="⌨ Keystrokes: ON" if not current else "⌨ Keystrokes: OFF",
            bg="#4a90e2" if not current else "#e74c3c",
        )

    def on_window_resize(event):
        if event.widget == root:
            new_width = video_frame.winfo_width()
            new_height = video_frame.winfo_height()
            aspect_ratio = preview_width / preview_height

            if new_width / new_height > aspect_ratio:
                canvas_height = new_height
                canvas_width = int(canvas_height * aspect_ratio)
            else:
                canvas_width = new_width
                canvas_height = int(canvas_width / aspect_ratio)

            video_canvas.configure(width=canvas_width, height=canvas_height)

    root.bind("<Configure>", on_window_resize)
    controls_frame = tk.Frame(
        main_container, bg=style["frame_bg"], relief="ridge", bd=2
    )
    controls_frame.pack(fill="x", pady=(0, style["padding"]))

    buttons_frame = tk.Frame(main_container, bg=style["frame_bg"], relief="ridge", bd=2)
    buttons_frame.pack(fill="x")
    for slider in [x_slider, y_slider, spacing_slider]:
        slider.pack(fill="x", expand=True, padx=5)

    def switch_camera(camera_width: int, camera_height: int):
        global cap, current_camera_index
        current_camera_index = int(camera_var.get())
        cap.release()
        cap = cv2.VideoCapture(current_camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
        if not cap.isOpened():
            messagebox.showerror(
                "Camera Error", "Failed to access the selected camera."
            )

    camera_var.trace_add(
        "write",
        lambda *args: switch_camera(
            camera_width=camera_width, camera_height=camera_height
        ),
    )

    return (
        root,
        video_canvas,
        x_slider,
        y_slider,
        width_var,
        spacing_slider,
        keystrokes_enabled,
        chuniio_enabled,
        update_rate,
    )


def calibrate(frame):
    global zone_color_state
    zone_color_state = []
    for zone in zones:
        brightness = get_avg_brightness(frame, zone)
        zone_color_state.append(brightness)
    print("Calibration completed. Initial lighting values:", zone_color_state)


def update_frame(
    preview_width,
    preview_height,
    chuniio_shared_memory,
):
    global cap
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not capture frame.")
        return

    frame = cv2.flip(frame, 1)
    x_offset = x_slider.get()
    y_offset = y_slider.get()
    spacing = spacing_slider.get()

    # Update zone positions
    for i, zone in enumerate(zones):
        zone["x"] = base_positions[i]["x"] + x_offset
        zone["y"] = base_positions[0]["y"] + y_offset + i * spacing

    # Process zones
    for i, zone in enumerate(zones):
        current_brightness = get_avg_brightness(frame, zone)
        if abs(current_brightness - zone_color_state[i]) > 20:
            if not ZONE_TRIGGERED_STATE[i]:
                if keystrokes_enabled.get():
                    print(f"Key '{_UMIGIRI_32_AIRZONE_LAYOUT[i]}' pressed.")
                    keyboard.press(_UMIGIRI_32_AIRZONE_LAYOUT[i])
                print(f"Zone {i} triggered")
                ZONE_TRIGGERED_STATE[i] = True
            cv2.rectangle(
                frame,
                (zone["x"], zone["y"]),
                (zone["x"] + zone["width"], zone["y"] + zone["height"]),
                (0, 255, 0),
                3,
            )
        else:
            if ZONE_TRIGGERED_STATE[i]:
                if keystrokes_enabled.get():
                    keyboard.release(_UMIGIRI_32_AIRZONE_LAYOUT[i])
                    print(f"Key '{_UMIGIRI_32_AIRZONE_LAYOUT[i]}' released.")
                ZONE_TRIGGERED_STATE[i] = False
            cv2.rectangle(
                frame,
                (zone["x"], zone["y"]),
                (zone["x"] + zone["width"], zone["y"] + zone["height"]),
                (0, 0, 255),
                2,
            )

    if chuniio_enabled.get():
        chuniio.write_to_airzone(ZONE_TRIGGERED_STATE, chuniio_shared_memory)

    # Convert to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Get canvas dimensions
    canvas_width = video_canvas.winfo_width()
    canvas_height = video_canvas.winfo_height()

    # Ensure valid dimensions before resizing
    if canvas_width <= 0 or canvas_height <= 0:
        canvas_width = preview_width
        canvas_height = preview_height

    # Calculate aspect ratio preserving dimensions
    aspect_ratio = frame.shape[1] / frame.shape[0]
    if canvas_width / canvas_height > aspect_ratio:
        display_height = canvas_height
        display_width = int(display_height * aspect_ratio)
    else:
        display_width = canvas_width
        display_height = int(display_width / aspect_ratio)

    # Ensure minimum dimensions
    display_width = max(display_width, 1)
    display_height = max(display_height, 1)

    # Resize frame
    try:
        rgb_frame = cv2.resize(rgb_frame, (display_width, display_height))
    except cv2.error as e:
        print(f"Resize error: {display_width}x{display_height}")
        return

    # Display frame
    img = ImageTk.PhotoImage(Image.fromarray(rgb_frame))
    video_canvas.delete("all")
    video_canvas.create_image(
        canvas_width // 2, canvas_height // 2, anchor="center", image=img
    )
    video_canvas.image = img

    try:
        rate = max(1, int(update_rate.get()))
    except ValueError:
        rate = 5
    root.after(rate, update_frame, preview_width, preview_height, chuniio_shared_memory)


def load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def main():
    global \
        root, \
        current_camera_index, \
        keystrokes_enabled, \
        chuniio_enabled, \
        video_canvas, \
        x_slider, \
        y_slider, \
        width_var, \
        spacing_slider, \
        cap, \
        update_rate, \
        CAMERA_WIDTH, \
        CAMERA_HEIGHT
    print("Now starting up... please wait a bit...")
    config = load_config()
    current_camera_index = config.get("camera_index", 0)
    cap = cv2.VideoCapture(current_camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 30)
    preview_width, preview_height = calculate_preview_size(CAMERA_WIDTH, CAMERA_HEIGHT)

    actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    if actual_width != CAMERA_WIDTH or actual_height != CAMERA_HEIGHT:
        print(
            f"Resolution {CAMERA_WIDTH}x{CAMERA_HEIGHT} not supported. Using {actual_width}x{actual_height}."
        )
        CAMERA_WIDTH = int(actual_width)
        CAMERA_HEIGHT = int(actual_height)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, actual_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, actual_height)
    ret, frame = cap.read()
    if ret:
        calibrate(frame)
    else:
        print("Error: Could not capture initial frame. Check your camera.")

    (
        root,
        video_canvas,
        x_slider,
        y_slider,
        width_var,
        spacing_slider,
        keystrokes_enabled,
        chuniio_enabled,
        update_rate,
    ) = setup_gui(CAMERA_WIDTH, CAMERA_HEIGHT, preview_width, preview_height)

    x_slider.set(config.get("x_offset", 0))
    y_slider.set(config.get("y_offset", 0))
    spacing_slider.set(config.get("spacing", 100))
    chuniio_enabled.set(config.get("chuniio_enabled", True))
    chuniio_shared_memory = chuniio.open_sharedmem() if chuniio_enabled.get() else None
    width_var.set(str(config.get("width", 50)))
    for zone in zones:
        zone["width"] = int(width_var.get())
    update_frame(preview_width, preview_height, chuniio_shared_memory)
    root.mainloop()
    cap.release()


main()
