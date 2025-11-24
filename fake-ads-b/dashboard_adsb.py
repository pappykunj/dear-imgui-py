import sys
import multiprocessing
from multiprocessing import Manager, Process
import threading
import time
from collections import deque
import random

def get_plane_color(hexid):
    """Generate a consistent color per plane."""
    random.seed(hexid)  # ensures same color for same hexid every time
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

# -------------------------
# ADS-B fake reader (for testing)
# -------------------------
def run_fake_adsb_reader(shared_planes):
    import random
    while True:
        for i in range(5):
            hexid = f"AB{i:03d}"
            shared_planes[hexid] = {
                "callsign": f"PLN{i:03d}",
                "lat": random.uniform(-90, 90),
                "lon": random.uniform(-180, 180),
                "alt": random.uniform(1000, 10000),
                "vel": random.uniform(100, 300),
                "ts": time.time()
            }
        time.sleep(1)

# -------------------------
# Map process (PyQt6 + Folium)
# -------------------------
def run_map_process(shared_planes):
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtCore import QTimer
    import folium
    from io import BytesIO

    class MapWindow(QMainWindow):
        def __init__(self, shared):
            super().__init__()
            self.shared = shared
            self.setWindowTitle("Live ADS-B Map")
            self.resize(900, 750)
            self.web = QWebEngineView()
            self.setCentralWidget(self.web)

            self.center = [20, 0]  # initial map center
            self.update_map()      # create map once

            # Update map every 30 seconds
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_map)
            self.timer.start(30000)

        def update_map(self):
            items = list(self.shared.items())
            if items:
                lats = [v['lat'] for _, v in items if v.get('lat') is not None]
                lons = [v['lon'] for _, v in items if v.get('lon') is not None]
                if lats and lons:
                    avg_lat = sum(lats)/len(lats)
                    avg_lon = sum(lons)/len(lons)
                    # Only recenter if plane moves far (>5 degrees)
                    if abs(avg_lat - self.center[0]) > 5 or abs(avg_lon - self.center[1]) > 5:
                        self.center = [avg_lat, avg_lon]

            # Create map at fixed/smooth center
            m = folium.Map(location=self.center, zoom_start=5)

            # Add plane markers
            for hexid, rec in items[:300]:
                lat, lon = rec.get('lat'), rec.get('lon')
                if lat is None or lon is None:
                    continue
                color = get_plane_color(hexid)
                popup = f"{rec.get('callsign', hexid)}<br>alt: {rec.get('alt',0.0)} m<br>vel: {rec.get('vel',0.0)} m/s"
                folium.CircleMarker(location=[lat, lon], radius=4, color=color, fill=True, fill_color=color, popup=popup).add_to(m)

            data = BytesIO()
            m.save(data, close_file=False)
            self.web.setHtml(data.getvalue().decode())

    app = QApplication(sys.argv)
    win = MapWindow(shared_planes)
    win.show()
    app.exec()

# -------------------------
# Dashboard (Pygame + PyImgui)
# -------------------------
def run_dashboard(shared_planes):
    import pygame
    from pygame.locals import OPENGL, DOUBLEBUF
    from OpenGL import GL
    import imgui
    from imgui.integrations.pygame import PygameRenderer
    import numpy as np

    pygame.init()
    width, height = 1000, 750  # window sizes
    screen = pygame.display.set_mode((width, height), OPENGL | DOUBLEBUF)

    imgui.create_context()
    renderer = PygameRenderer()
    clock = pygame.time.Clock()

    # Fix display size for ImGui
    io = imgui.get_io()
    io.display_size = pygame.display.get_window_size()

    # -------------------------
    # State
    # -------------------------
    histories = {}
    selected_planes = []
    map_process = None

    def sync_histories():
        for hexid, rec in list(shared_planes.items()):
            if hexid not in histories:
                histories[hexid] = {
                    'alt': deque([0.0]*200, maxlen=200),
                    'vel': deque([0.0]*200, maxlen=200),
                    'ts': deque([0.0]*200, maxlen=200),
                    'callsign': rec.get('callsign', hexid)
                }
            else:
                histories[hexid]['callsign'] = rec.get('callsign', histories[hexid]['callsign'])

    def update_histories():
        for hexid, rec in list(shared_planes.items()):
            h = histories.get(hexid)
            if h:
                h['alt'].append(float(rec.get('alt',0.0)))
                h['vel'].append(float(rec.get('vel',0.0)))
                h['ts'].append(float(rec.get('ts',time.time())))

    def auto_select_top_n(n=3):
        items = sorted(shared_planes.items(), key=lambda kv: kv[1].get('ts',0.0), reverse=True)
        return [kv[0] for kv in items[:n]]

    selected_planes = auto_select_top_n(3)

    # -------------------------
    # Main loop
    # -------------------------
    running = True
    while running:
        io.display_size = pygame.display.get_window_size()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            renderer.process_event(e)

        sync_histories()
        update_histories()

        imgui.new_frame()

        # ---------- Menu Bar ----------
        if imgui.begin_main_menu_bar():
            if imgui.begin_menu("File", True):
                if imgui.menu_item("Open Map")[0]:
                    if map_process is None or not map_process.is_alive():
                        map_process = multiprocessing.Process(target=run_map_process, args=(shared_planes,), daemon=True)
                        map_process.start()
                if imgui.menu_item("Refresh Map")[0]:
                    if map_process and map_process.is_alive():
                        map_process.terminate()
                    map_process = multiprocessing.Process(target=run_map_process, args=(shared_planes,), daemon=True)
                    map_process.start()
                if imgui.menu_item("Quit")[0]:
                    running = False
                imgui.end_menu()
            imgui.end_main_menu_bar()

        # ---------- Dashboard Columns ----------
        imgui.begin("ADS-B Dashboard")

        imgui.columns(2, "dashboard_cols", border=True)
        col1_width = 400  # left: plane list + stats
        col2_width = 580  # right: plots
        imgui.set_column_width(0, col1_width)

        # ---------- Left Column: Plane List ----------
        imgui.begin_child("plane_list_child", width=col1_width, height=700, border=True)
        imgui.text("Tracked Planes")
        imgui.separator()

        # Plane checkboxes
        items_sorted = sorted(shared_planes.items(), key=lambda kv: kv[1].get('ts',0.0), reverse=True)
        for hexid, rec in items_sorted[:500]:
            cs = rec.get('callsign') or hexid
            selected = hexid in selected_planes
            changed, val = imgui.checkbox(f"{cs} ({hexid})", selected)
            if changed:
                if val and hexid not in selected_planes:
                    selected_planes.append(hexid)
                elif not val and hexid in selected_planes:
                    selected_planes.remove(hexid)

        imgui.separator()
        imgui.text(f"Total planes tracked: {len(shared_planes)}")
        imgui.text(f"Selected planes: {len(selected_planes)}")
        imgui.end_child()

        imgui.next_column()

       # ---------- Right Column: Fixed-size Plots ----------
        imgui.begin_child("plane_plots_child", width=col2_width, height=700, border=True)
        imgui.text("Selected Plane Data")
        imgui.separator()

        if imgui.button("Auto-select top 3"):
            selected_planes = auto_select_top_n(3)
        imgui.same_line()
        if imgui.button("Clear selection"):
            selected_planes = []

        for hexid in selected_planes:
            h = histories.get(hexid)
            if not h:
                continue
            cs = h.get('callsign', hexid)
            imgui.text(f"{cs} ({hexid})")
            imgui.spacing()
            # Fixed-size plots
            imgui.plot_lines(f"Altitude (m) - {hexid}", np.array(h['alt'], dtype=np.float32), graph_size=(550, 180))
            imgui.plot_lines(f"Velocity (m/s) - {hexid}", np.array(h['vel'], dtype=np.float32), graph_size=(550, 140))
            imgui.separator()
            imgui.spacing()

        imgui.end_child()
        imgui.columns(1)
        imgui.end()

        # ---------- Render ----------
        GL.glClearColor(0.95,0.95,0.95,1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        imgui.render()
        renderer.render(imgui.get_draw_data())
        pygame.display.flip()
        clock.tick(30)

    # Cleanup
    if map_process and map_process.is_alive():
        map_process.terminate()
    pygame.quit()

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    multiprocessing.freeze_support()
    manager = Manager()
    shared_planes = manager.dict()

    # Start fake ADS-B feed
    p_reader = multiprocessing.Process(target=run_fake_adsb_reader, args=(shared_planes,), daemon=True)
    p_reader.start()

    run_dashboard(shared_planes)
