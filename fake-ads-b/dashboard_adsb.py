import sys
import multiprocessing
from multiprocessing import Manager, Process
import time
from collections import deque
import threading

def run_fake_adsb_reader(shared_planes):
    import random, time
    while True:
        for i in range(5):  # 5 planes
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
# ADS-B feed reader process
# -------------------------      
def run_adsb_reader_multi(shared_planes, feeds):
    import socket

    def connect_and_read(host, port):
        while True:
            try:
                sock = socket.create_connection((host, port), timeout=10)
                file = sock.makefile("r", encoding="utf-8", newline="\n")
                print(f"[ADSB] connected to {host}:{port}")
                for line in file:
                    try:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split(',')
                        if parts[0] != "MSG":
                            continue
                        msg_subtype = parts[1]
                        if msg_subtype not in ("2","3","4"):
                            continue
                        hexid = parts[4].strip()
                        if not hexid:
                            continue
                        callsign = parts[10].strip() if len(parts) > 10 and parts[10].strip() else hexid
                        alt = float(parts[11]) if parts[11] else 0.0
                        vel = float(parts[12]) if parts[12] else 0.0
                        lat = float(parts[14]) if parts[14] else None
                        lon = float(parts[15]) if parts[15] else None

                        record = shared_planes.get(hexid, {})
                        record.update({
                            "callsign": callsign,
                            "alt": alt or record.get("alt", 0.0),
                            "vel": vel or record.get("vel", 0.0),
                            "lat": lat if lat is not None else record.get("lat", None),
                            "lon": lon if lon is not None else record.get("lon", None),
                            "ts": time.time()
                        })
                        shared_planes[hexid] = record
                    except Exception:
                        continue
            except Exception as e:
                print(f"[ADSB] connection error {host}:{port} -> {e}, retrying in 5s")
                time.sleep(5)

    # start a thread per feed
    threads = []
    for host, port in feeds:
        t = threading.Thread(target=connect_and_read, args=(host, port), daemon=True)
        t.start()
        threads.append(t)

    while True:
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
            self.resize(900, 700)
            self.web = QWebEngineView()
            self.setCentralWidget(self.web)
            self.update_map()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_map)
            self.timer.start(3000)

        def update_map(self):
            items = list(self.shared.items())
            if not items:
                m = folium.Map(location=[20,0], zoom_start=2)
            else:
                lats = [v['lat'] for _,v in items if v.get('lat') is not None]
                lons = [v['lon'] for _,v in items if v.get('lon') is not None]
                center = [sum(lats)/len(lats), sum(lons)/len(lons)] if lats and lons else [20,0]
                m = folium.Map(location=center, zoom_start=5)
                for hexid, rec in items[:300]:
                    lat = rec.get('lat')
                    lon = rec.get('lon')
                    if lat is None or lon is None:
                        continue
                    alt = rec.get('alt',0.0)
                    vel = rec.get('vel',0.0)
                    cs = rec.get('callsign', hexid)
                    popup = f"{cs}<br>alt: {alt} m<br>vel: {vel} m/s"
                    folium.CircleMarker(location=[lat, lon], radius=4, color="red", fill=True, popup=popup).add_to(m)
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
def run_dashboard(shared_planes, width=1100, height=750, max_points=200):
    import pygame
    from pygame.locals import OPENGL, DOUBLEBUF
    from OpenGL import GL
    import imgui
    from imgui.integrations.pygame import PygameRenderer
    import numpy as np

    pygame.init()
    size = (width, height)
    pygame.display.set_mode(size, OPENGL | DOUBLEBUF)
    imgui.create_context()
    renderer = PygameRenderer()
    io = imgui.get_io()
    io.display_size = size

    histories = {}
    selected_planes = []
    clock = pygame.time.Clock()

    def sync_histories():
        for hexid, rec in list(shared_planes.items()):
            if hexid not in histories:
                histories[hexid] = {
                    'alt': deque([0.0]*max_points,maxlen=max_points),
                    'vel': deque([0.0]*max_points,maxlen=max_points),
                    'ts': deque([0.0]*max_points,maxlen=max_points),
                    'callsign': rec.get('callsign', hexid)
                }
            else:
                histories[hexid]['callsign'] = rec.get('callsign', histories[hexid]['callsign'])

    def update_histories_from_shared():
        for hexid, rec in list(shared_planes.items()):
            h = histories.get(hexid)
            if not h:
                continue
            try:
                h['alt'].append(float(rec.get('alt',0.0)))
                h['vel'].append(float(rec.get('vel',0.0)))
                h['ts'].append(float(rec.get('ts',time.time())))
            except Exception:
                h['alt'].append(0.0); h['vel'].append(0.0); h['ts'].append(time.time())

    def auto_select_top_n(n=3):
        items = sorted(shared_planes.items(), key=lambda kv: kv[1].get('ts',0.0), reverse=True)
        return [kv[0] for kv in items[:n]]

    selected_planes = auto_select_top_n(3)

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            renderer.process_event(e)

        sync_histories()
        update_histories_from_shared()

        imgui.new_frame()
        imgui.begin("Multi-Feed ADS-B Dashboard", flags=imgui.WINDOW_ALWAYS_AUTO_RESIZE)
        imgui.text("Tracked planes (recent first)")

        imgui.begin_child("plane_list", width=500, height=400, border=True)
        items = sorted(shared_planes.items(), key=lambda kv: kv[1].get('ts',0.0), reverse=True)
        for hexid, rec in items[:500]:
            cs = rec.get('callsign') or hexid
            selected = hexid in selected_planes
            changed, val = imgui.checkbox(f"{cs} ({hexid})", selected)
            if changed:
                if val and hexid not in selected_planes:
                    selected_planes.append(hexid)
                elif not val and hexid in selected_planes:
                    selected_planes.remove(hexid)
        imgui.end_child()

        if imgui.button("Auto-select top 3"):
            selected_planes = auto_select_top_n(3)
        imgui.same_line()
        if imgui.button("Clear selection"):
            selected_planes = []

        imgui.separator()
        for hexid in selected_planes:
            h = histories.get(hexid)
            if not h:
                continue
            cs = h.get('callsign', hexid)
            imgui.text(f"{cs} ({hexid})")
            imgui.plot_lines(f"alt_{hexid}", np.array(h['alt'],dtype=np.float32), graph_size=(500,200))
            imgui.plot_lines(f"vel_{hexid}", np.array(h['vel'],dtype=np.float32), graph_size=(500,160))
            imgui.separator()

        imgui.text(f"Total planes tracked: {len(shared_planes)}")
        imgui.text(f"Selected to plot: {len(selected_planes)}")
        imgui.end()

        imgui.render()
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        renderer.render(imgui.get_draw_data())
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    multiprocessing.freeze_support()
    manager = Manager()
    shared_planes = manager.dict()

    feeds = [
        ("127.0.0.1", 30003),          # local dump1090
        ("opensky-network.org", 30003) # OpenSky
    ]

    p_reader = Process(target=run_fake_adsb_reader, args=(shared_planes,), daemon=True)
    p_reader.start()

    p_map = Process(target=run_map_process, args=(shared_planes,), daemon=True)
    p_map.start()

    try:
        run_dashboard(shared_planes)
    finally:
        try: p_reader.terminate()
        except Exception: pass
        try: p_map.terminate()
        except Exception: pass
