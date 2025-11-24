# ImGui + GLFW Python Example

This repository contains a complete, standalone example demonstrating how to use **Dear ImGui** with **GLFW** in Python. It covers basic GUI elements, window layouts, state management, and controls, making it ideal as a reference for building interactive desktop applications.

---

## Features

The example includes:

- **Example Window**: Basic ImGui window displaying text.
- **Layout Example**: Demonstrates columns, same-line buttons, spacing, and child windows.
- **State Example**: Shows how to use checkboxes, sliders, and text input with Python state variables.
- **Controls**: Includes combo boxes, listboxes, numeric/text inputs, sliders, buttons, and colored text.
- **Menu Bar**: Simple `File` and `Edit` menus with basic actions.
- **Window Flags Controls**: Toggle `no_titlebar`, `no_resize`, and `no_move` flags for a window dynamically.
- **Demo Window Support**: Optional ImGui demo window for testing features.
- Cross-binding safe wrappers for features like `imgui.begin` and `text_colored`.

---

## Screenshot

![ImGui GLFW Example Screenshot](controls_dashboard.png)

---

## Requirements

- Python 3.7+
- Packages:

```bash
pip install imgui[full] glfw PyOpenGL
