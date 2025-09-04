# Boundary Creation UI (Qt6)

A desktop application for loading DXF files, extracting point data, and generating **alpha shape boundaries** interactively.  
Built with **PySide6 (Qt6)**, **matplotlib**, and **alphashape**.

---

## ✨ Features
- Load DXF files and extract geometry points (Lines, LWPOLYLINE, POLYLINE).
- Interactive **alpha shape boundary** computation.
- Adjustable alpha parameter for boundary precision.
- Scatter plot visualization of DXF points and computed boundaries.
- Export computed boundaries as DXF with a closed polyline.

---

## 🖼️ Screenshot
(Add a screenshot here if available)

---

## 📦 Requirements

Install dependencies:

```bash
pip install PySide6 matplotlib numpy shapely ezdxf alphashape
or
pip install -r requirements.txt

🛠️ Tech Stack

PySide6 (Qt6) - GUI framework
matplotlib - Visualization
shapely & alphashape - Geometry computation
ezdxf - DXF parsing
