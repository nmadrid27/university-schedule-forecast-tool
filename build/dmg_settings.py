import os
app = os.path.join("dist", "SCAD Forecast Tool.app")
files = [app]
symlinks = {"Applications": "/Applications"}
icon_locations = {"SCAD Forecast Tool.app": (140, 120), "Applications": (500, 120)}
window_rect = ((100, 100), (640, 280))
