import sys
import traceback
import numpy as np
import matplotlib
matplotlib.use("QtAgg")

# from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from shapely.geometry import MultiPolygon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QFileDialog, QVBoxLayout,
    QHBoxLayout, QProgressBar, QTextEdit, QLabel, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
import ezdxf
import alphashape


# ---------- Worker Thread for DXF Loading ----------
class LoaderThread(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished_loading = Signal(np.ndarray)

    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    def run(self):
        try:
            self.log.emit(f"Loading DXF: {self.filename}")
            doc = ezdxf.readfile(self.filename)
            msp = doc.modelspace()
            pts = []
            total = len(msp)
            for idx, e in enumerate(msp):
                t = e.dxftype()
                if t == "LINE":
                    pts.append([e.dxf.start.x, e.dxf.start.y])
                    pts.append([e.dxf.end.x, e.dxf.end.y])
                elif t == "LWPOLYLINE":
                    for x, y, *_ in e:
                        pts.append([x, y])
                elif t == "POLYLINE":
                    for v in e.vertices:
                        pts.append([v.dxf.location.x, v.dxf.location.y])
                if total > 0:
                    self.progress.emit(int((idx / total) * 100))
            self.finished_loading.emit(np.array(pts))
        except Exception as e:
            self.log.emit(f"Error: {e}")
            self.log.emit(traceback.format_exc())


# ---------- Matplotlib Widget ----------
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class MplCanvas(QWidget):
    def __init__(self):
        super().__init__()

        # Create figure and FigureCanvas
        self.fig = Figure(figsize=(6, 4))
        self.ax = self.fig.add_subplot(111)
        self._canvas = FigureCanvasQTAgg(self.fig)  # This is the actual canvas

        # Wrap canvas in a QWidget layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)
        self.setLayout(layout)

        # Configure plot
        self.ax.set_title("Alpha Shape Boundary")
        self.ax.set_aspect("equal")

    def draw(self):
        """Helper to redraw the canvas."""
        self._canvas.draw()


# ---------- Main Window ----------
class BoundaryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Boundary Creation (Qt6)")
        self.points = None

        # ---- Define Widgets First ----
        self.alpha_input = QLineEdit("0.2")
        self.load_btn = QPushButton("Load DXF")
        self.refresh_btn = QPushButton("Refresh Plot")
        self.export_btn = QPushButton("Export Boundary")
        self.progress = QProgressBar()
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.canvas = MplCanvas()

        # ---- Layout ----
        main_layout = QVBoxLayout()

        # Controls row
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.load_btn)
        controls_layout.addWidget(QLabel("Alpha:"))
        controls_layout.addWidget(self.alpha_input)
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addWidget(self.export_btn)

        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.progress)

        # Plot row
        self.canvas.setMinimumHeight(500)
        main_layout.addWidget(self.canvas, stretch=3)

        # Logs row
        log_label = QLabel("Logs:")
        main_layout.addWidget(log_label)
        self.log_box.setMaximumHeight(150)
        main_layout.addWidget(self.log_box, stretch=1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # ---- Connections ----
        self.load_btn.clicked.connect(self.load_dxf)
        self.refresh_btn.clicked.connect(self.refresh_plot)
        self.export_btn.clicked.connect(self.export_boundary)


    def log(self, msg):
        self.log_box.append(msg)
        print(msg)

    def compute_alpha_shape(self, points, alpha):
        if len(points) < 4:
            return None
        shape = alphashape.alphashape(points, float(alpha))
        if shape.is_empty:
            return None
        if isinstance(shape, MultiPolygon):
            shape = max(shape.geoms, key=lambda g: g.area)
        return np.array(shape.exterior.coords)

    def load_dxf(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select DXF File", "", "DXF Files (*.dxf)")
        if not filename:
            return
        self.progress.setValue(0)
        self.worker = LoaderThread(filename)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(self.log)
        self.worker.finished_loading.connect(self.on_points_loaded)
        self.worker.start()

    def on_points_loaded(self, points):
        self.points = points
        self.log(f"Loaded {len(points)} points.")
        self.refresh_plot()

    def refresh_plot(self):
        if self.points is None or len(self.points) == 0:
            self.log("No points to plot.")
            return
        try:
            alpha = float(self.alpha_input.text())
        except ValueError:
            self.log("Invalid alpha value.")
            return

        boundary = self.compute_alpha_shape(self.points, alpha)
        self.canvas.ax.clear()
        self.canvas.ax.scatter(self.points[:, 0], self.points[:, 1], s=1, c='blue')
        if boundary is not None:
            self.canvas.ax.plot(boundary[:, 0], boundary[:, 1], 'r-', lw=2)
        self.canvas.ax.set_title("Alpha Shape Boundary")
        self.canvas.ax.set_aspect("equal")
        self.canvas.draw()  # ✅ FIXED
        self.log(f"Plot refreshed with alpha={alpha}")


    def export_boundary(self):
        if self.points is None:
            self.log("No data to export.")
            return
        try:
            alpha = float(self.alpha_input.text())
        except ValueError:
            self.log("Invalid alpha value.")
            return

        boundary = self.compute_alpha_shape(self.points, alpha)
        if boundary is None or len(boundary) < 3:
            self.log("No valid boundary to export.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Boundary As", "", "DXF Files (*.dxf)")
        if not out_path:
            return

        try:
            with open(out_path, "w") as f:
                f.write("0\nSECTION\n2\nENTITIES\n")
                f.write("0\nLWPOLYLINE\n8\n0\n")
                f.write(f"90\n{len(boundary)}\n70\n1\n")
                for x, y in boundary:
                    f.write(f"10\n{x}\n20\n{y}\n")
                f.write("0\nENDSEC\n0\nEOF\n")
            self.log(f"Boundary exported to {out_path}")
        except Exception as e:
            self.log(f"Export error: {e}")
            QMessageBox.critical(self, "Error", str(e))


# ---------- Run ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BoundaryApp()
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec())
