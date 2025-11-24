import dearpygui.dearpygui as dpg
import time
import random
from threading import Thread

# --- Game settings ---
GRID_WIDTH = 20
GRID_HEIGHT = 10
CELL_SIZE = 25
UPDATE_INTERVAL = 0.25  # Initial speed
MIN_INTERVAL = 0.05
MAX_INTERVAL = 0.5

# --- Game state ---
snake = [(5, 5)]
direction = (1, 0)
food = (random.randint(0, GRID_WIDTH-1), random.randint(0, GRID_HEIGHT-1))
score = 0
game_over = False
game_running = True

# --- Helper functions ---
def reset_game():
    global snake, direction, food, score, game_over, game_running
    snake = [(5, 5)]
    direction = (1, 0)
    food = (random.randint(0, GRID_WIDTH-1), random.randint(0, GRID_HEIGHT-1))
    score = 0
    game_over = False
    game_running = True

def move_snake():
    global snake, food, score, game_over
    if not game_running or game_over:
        return

    head_x, head_y = snake[-1]
    dx, dy = direction
    new_head = (head_x + dx, head_y + dy)

    # Collision check
    if (new_head in snake or 
        not (0 <= new_head[0] < GRID_WIDTH) or 
        not (0 <= new_head[1] < GRID_HEIGHT)):
        game_over = True
        dpg.configure_item("end_game_popup", show=True)
        dpg.set_value("final_score", f"Score: {score}")
        return

    snake.append(new_head)

    if new_head == food:
        score += 1
        place_food()
    else:
        snake.pop(0)

def place_food():
    global food
    while True:
        new_food = (random.randint(0, GRID_WIDTH-1), random.randint(0, GRID_HEIGHT-1))
        if new_food not in snake:
            food = new_food
            break

# --- Direction handlers ---
def go_up():
    global direction
    if direction != (0, 1):
        direction = (0, -1)

def go_down():
    global direction
    if direction != (0, -1):
        direction = (0, 1)

def go_left():
    global direction
    if direction != (1, 0):
        direction = (-1, 0)

def go_right():
    global direction
    if direction != (-1, 0):
        direction = (1, 0)

# --- Key handler for WSAD ---
def key_down_handler(sender, app_data):
    if app_data == 87:  # W
        go_up()
    elif app_data == 83:  # S
        go_down()
    elif app_data == 65:  # A
        go_left()
    elif app_data == 68:  # D
        go_right()

# --- Adjust speed via slider ---
def adjust_speed(sender, app_data):
    global UPDATE_INTERVAL
    UPDATE_INTERVAL = MAX_INTERVAL - app_data * (MAX_INTERVAL - MIN_INTERVAL)

# --- GUI drawing ---
def draw_game():
    dpg.delete_item("game_canvas", children_only=True)

    dpg.draw_rectangle((0,0),(GRID_WIDTH*CELL_SIZE, GRID_HEIGHT*CELL_SIZE),
                       color=(255,255,0,255), thickness=3, parent="game_canvas")
    
    for i, (x, y) in enumerate(snake):
        color = (0, 255, 0, 255) if i < len(snake)-1 else (0, 150, 255, 255)
        dpg.draw_rectangle((x*CELL_SIZE, y*CELL_SIZE),
                           ((x+1)*CELL_SIZE, (y+1)*CELL_SIZE),
                           color=color, fill=color, parent="game_canvas")
    
    fx, fy = food
    dpg.draw_rectangle((fx*CELL_SIZE, fy*CELL_SIZE),
                       ((fx+1)*CELL_SIZE, (fy+1)*CELL_SIZE),
                       color=(255,0,0,255), fill=(255,0,0,255),
                       parent="game_canvas")
    
    dpg.set_value("score_text", f"Score: {score}")

# --- Game loop ---
def game_loop():
    while dpg.is_dearpygui_running():
        if game_running:
            move_snake()
            draw_game()
        time.sleep(UPDATE_INTERVAL)

# --- Menu actions ---
def menu_refresh():
    reset_game()

def menu_exit():
    dpg.stop_dearpygui()

def open_help():
    dpg.configure_item("help_window", show=True)

# --- End game popup ---
def restart_game_callback():
    reset_game()
    dpg.configure_item("end_game_popup", show=False)

# GUI 

dpg.create_context()
dpg.create_viewport(title="Snake Game",
                    width=GRID_WIDTH*CELL_SIZE + 250,
                    height=GRID_HEIGHT*CELL_SIZE + 250)

with dpg.window(label="Snake Game", tag="game_window"):
    with dpg.menu_bar():
        with dpg.menu(label="File"):
            dpg.add_menu_item(label="Refresh", callback=menu_refresh)
            dpg.add_menu_item(label="Exit", callback=menu_exit)
        with dpg.menu(label="Help"):
            dpg.add_menu_item(label="How to Play", callback=open_help)

    with dpg.group(horizontal=True):
        with dpg.drawlist(width=GRID_WIDTH*CELL_SIZE, height=GRID_HEIGHT*CELL_SIZE, tag="game_canvas"):
            pass

     
        with dpg.group(horizontal=False):  # vertical group: top row + bottom row
            # Top row: Up button, shifted right
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=60)  # horizontal padding from left
                btn_up = dpg.add_button(label="Up", width=60, callback=go_up)
                with dpg.tooltip(btn_up):
                    dpg.add_text("W")

            # Bottom row: Left, Down, Right
            with dpg.group(horizontal=True):
                btn_left = dpg.add_button(label="Left", width=60, callback=go_left)
                with dpg.tooltip(btn_left):
                    dpg.add_text("A")

                btn_down = dpg.add_button(label="Down", width=60, callback=go_down)
                with dpg.tooltip(btn_down):
                    dpg.add_text("S")

                btn_right = dpg.add_button(label="Right", width=60, callback=go_right)
                with dpg.tooltip(btn_right):
                    dpg.add_text("D")


            # Speed slider
            dpg.add_text("Speed")
            dpg.add_slider_float(label="", default_value=0.5, min_value=0, max_value=1, width=100, callback=adjust_speed)

    dpg.add_text("Score: 0", tag="score_text")

# --- Key handler registry ---
with dpg.handler_registry():
    dpg.add_key_down_handler(callback=key_down_handler)

# --- End game popup ---
with dpg.window(label="Game Over", modal=True, show=False, tag="end_game_popup", no_close=True, width=300, height=150):
    dpg.add_text("", tag="final_score")
    dpg.add_text("You hit the wall or yourself!")
    dpg.add_spacer(height=10)
    dpg.add_button(label="Restart", callback=restart_game_callback)
    dpg.add_button(label="Exit", callback=menu_exit)

# --- Help window ---
with dpg.window(label="How to Play", modal=True, show=False, tag="help_window", width=400, height=250):
    dpg.add_text("Snake Game Instructions:")
    dpg.add_text("1. Use W, A, S, D keys OR the arrow pad buttons to move the snake.")
    dpg.add_text("2. Eat red food to grow.")
    dpg.add_text("3. Avoid hitting the border or yourself.")
    dpg.add_text("4. Score is shown at the top.")
    dpg.add_text("5. Use the speed slider to adjust snake speed.")
    dpg.add_text("6. Restart after Game Over to play again.")
    dpg.add_text("7. Refresh from File menu.")

# --- Final init ---
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.focus_item("game_window")

Thread(target=game_loop, daemon=True).start()
dpg.start_dearpygui()
dpg.destroy_context()
