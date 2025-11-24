"""
Complete ImGui + GLFW example containing:
- Example Window
- Layout Example (columns, child)
- State Example (checkbox, slider, text input)
- Controls (combo, listbox, inputs, sliders, buttons)
- Menu bar (File / Edit)
- Window Flags controls (no_titlebar, no_resize, no_move)
All widget calls happen inside the frame. State variables are defined up top.
"""

import sys
import imgui
from imgui.integrations.glfw import GlfwRenderer
import glfw
import OpenGL.GL as gl


def initialize_glfw(width=800, height=600, title="ImGui + GLFW Example"):
    if not glfw.init():
        raise Exception("Could not initialize GLFW")

    # Optional: request a core profile context if needed for your GL bindings
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    glfw.window_hint(glfw.RESIZABLE, glfw.TRUE)
    window = glfw.create_window(width, height, title, None, None)

    if not window:
        glfw.terminate()
        raise Exception("Could not create GLFW window")

    glfw.make_context_current(window)
    return window


# -------------------- STATE (global) --------------------
# Generic UI state
checkbox_state = True
slider_value = 0.5
text_input = "Edit me"

# Window flags toggles
no_titlebar = False
no_resize = False
no_move = False

# Controls state
items = ["Option 1", "Option 2", "Option 3"]
current_index = 0

current_text = "Type here"
current_int = 10
current_float = 0.25
current_value = 0.75
checked_state = False

# Misc
show_demo_window = False  # if you want to show ImGui's built-in demo (if available)


# -------------------- UI RENDER FUNCTIONS --------------------
def safe_begin(title, *args, **kwargs):
    """
    Wrapper around imgui.begin to accept both return patterns:
    - older bindings: returns bool
    - newer bindings: returns (bool, open_state)
    Returns only the is_open boolean to the caller.
    """
    res = imgui.begin(title, *args, **kwargs)
    if isinstance(res, tuple):
        return res[0]
    return res


def render_menu_bar(window):
    """
    Renders a simple main menu bar with File and Edit menus.
    File->Open prints a message; File->Quit will close the window.
    """
    if imgui.begin_main_menu_bar():
        if imgui.begin_menu("File", True):
            clicked, _ = imgui.menu_item("Open", "Ctrl+O")
            if clicked:
                print("[Menu] Open requested")
            clicked_quit, _ = imgui.menu_item("Quit", "Alt+F4")
            if clicked_quit:
                glfw.set_window_should_close(window, True)
            imgui.end_menu()

        if imgui.begin_menu("Edit", True):
            # Placeholders for Edit menu
            if imgui.menu_item("Undo", "Ctrl+Z")[0]:
                print("[Menu] Undo")
            imgui.end_menu()

        imgui.end_main_menu_bar()


def render_layout_example():
    """
    Layout Example window: columns, buttons on same line, spacing, child window.
    """
    imgui.begin("Layout Example", True)

    # Columns: 2 columns example
    try:
        # Some bindings support imgui.columns; try-catch to be safe
        imgui.columns(2, "columns_example")
        imgui.text("Column 1")
        imgui.next_column()
        imgui.text("Column 2")
        imgui.columns(1)
    except Exception:
        # If columns unsupported, fallback to simple text
        imgui.text("Columns not supported in this binding; fallback shown.")

    # Same-line buttons
    if imgui.button("Left"):
        print("Left clicked")
    imgui.same_line()
    if imgui.button("Right"):
        print("Right clicked")

    # Spacing and dummy vertical space
    imgui.spacing()
    imgui.dummy(0.0, 10.0)

    # Child region
    if imgui.begin_child("child_example", width=200, height=100, border=True):
        imgui.text("Child content")
        imgui.text("More inside child...")
    imgui.end_child()

    imgui.end()


def render_state_example():
    """
    Window showing checkbox, slider, and text input that use the global state.
    """
    global checkbox_state, slider_value, text_input
    imgui.begin("State Example", True)

    changed, checkbox_state = imgui.checkbox("Checkbox", checkbox_state)
    changed, slider_value = imgui.slider_float("Slider", slider_value, 0.0, 1.0)
    changed, text_input = imgui.input_text("Text", text_input, 256)

    imgui.end()


def render_controls():
    """
    Controls window: combo, listbox, inputs, sliders, buttons, colored text.
    """
    global current_index, current_text, current_int, current_float, current_value, checked_state

    imgui.begin("Controls", True)

    # Combo box
    changed, current_index = imgui.combo("Combo", current_index, items)

    # Listbox
    changed, current_index = imgui.listbox("Listbox", current_index, items, height_in_items=4)

    # Text and numeric inputs
    changed, current_text = imgui.input_text("Input", current_text, 256)
    changed, current_int = imgui.input_int("Integer", current_int)
    changed, current_float = imgui.input_float("Float", current_float, step=0.1)

    # Sliders
    changed, current_value = imgui.slider_float("Slider", current_value, 0.0, 1.0)
    changed, current_int = imgui.slider_int("Int Slider", current_int, 0, 100)

    # Text display
    imgui.text("Basic text")
    # text_colored expects RGBA floats in [0,1]
    try:
        imgui.text_colored("Colored text", 1.0, 0.0, 0.0, 1.0)
    except Exception:
        # Some wrappers use a different name or signature; ignore if unavailable
        imgui.text("Colored text (red)")

    # Buttons
    if imgui.button("Click me"):
        print("Button clicked!")

    # Checkbox
    changed, checked_state = imgui.checkbox("Check me", checked_state)

    imgui.end()


def render_flags_window():
    """
    Small window to toggle window flags that will be applied to another window.
    """
    global no_titlebar, no_resize, no_move
    imgui.begin("Window Flags", True)
    _, no_titlebar = imgui.checkbox("No titlebar", no_titlebar)
    _, no_resize = imgui.checkbox("No resize", no_resize)
    _, no_move = imgui.checkbox("No move", no_move)
    imgui.end()


# -------------------- MAIN --------------------
def main():
    global show_demo_window

    imgui.create_context()
    window = initialize_glfw()
    impl = GlfwRenderer(window)

    # Main loop
    while not glfw.window_should_close(window):
        glfw.poll_events()
        impl.process_inputs()

        # Start new frame
        imgui.new_frame()

        # Optionally show ImGui's demo (helpful if available)
        if show_demo_window:
            try:
                imgui.show_demo_window()
            except Exception:
                pass

        # Render menu bar
        render_menu_bar(window)

        # Basic example window
        imgui.begin("Example Window", True)
        imgui.text("Hello from GLFW + ImGui!")
        imgui.end()

        # Layout example
        render_layout_example()

        # Controls
        render_controls()

        # State example
        render_state_example()

        # Flags window
        render_flags_window()

        # Build window_flags based on toggles
        window_flags = 0
        if no_titlebar:
            window_flags |= imgui.WINDOW_NO_TITLE_BAR
        if no_resize:
            window_flags |= imgui.WINDOW_NO_RESIZE
        if no_move:
            window_flags |= imgui.WINDOW_NO_MOVE

        # Begin a window with flags: safe begin to adapt to binding differences
        is_open = safe_begin("Window Title (with flags)", True, flags=window_flags)
        if is_open:
            imgui.text("Window content (flags applied here).")
            imgui.text("Toggle flags in the 'Window Flags' window.")
        imgui.end()

        # refresh & render
        gl.glClearColor(1.0, 1.0, 1.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        imgui.render()
        impl.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    # Close
    impl.shutdown()
    glfw.terminate()
    sys.exit(0)


if __name__ == "__main__":
    main()
