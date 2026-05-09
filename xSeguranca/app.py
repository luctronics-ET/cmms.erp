from __future__ import annotations

import asyncio
import io
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw
from pydantic import BaseModel


class CameraConfig(BaseModel):
    id: str
    name: str
    type: str
    thermal: bool
    position: dict[str, int]
    fov: dict[str, int]


class PTZCommand(BaseModel):
    pan: int = 0
    tilt: int = 0
    zoom: int = 0
    duration_ms: int = 250


CAMERAS: list[CameraConfig] = [
    CameraConfig(
        id="dome_1",
        name="Dome PTZ - Entrada",
        type="ptz",
        thermal=False,
        position={"x": 300, "y": 250},
        fov={"horizontal": 70, "vertical": 50},
    ),
    CameraConfig(
        id="dome_2",
        name="Dome PTZ Térmica - Perímetro",
        type="ptz",
        thermal=True,
        position={"x": 500, "y": 250},
        fov={"horizontal": 60, "vertical": 45},
    ),
]

PTZ_STATE: dict[str, dict[str, int]] = {camera.id: {"pan": 0, "tilt": 0, "zoom": 0} for camera in CAMERAS}
PUBLIC_DIR = Path(__file__).resolve().parent / "public"

app = FastAPI(title="xSeguranca API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")


def _camera_or_404(camera_id: str) -> CameraConfig | None:
    for camera in CAMERAS:
        if camera.id == camera_id:
            return camera
    return None


def _render_snapshot(camera: CameraConfig) -> bytes:
    image = Image.new("RGB", (960, 540), color=(7, 17, 31))
    draw = ImageDraw.Draw(image)
    accent = (0, 180, 216) if not camera.thermal else (239, 68, 68)
    draw.rectangle((24, 24, 936, 516), outline=accent, width=4)
    draw.text((40, 40), "CMASM xSeguranca", fill=(220, 230, 240))
    draw.text((40, 84), camera.name, fill=accent)
    draw.text((40, 118), f"Camera: {camera.id}", fill=(180, 190, 200))
    draw.text((40, 152), f"Modo: {'Termica' if camera.thermal else 'RGB'}", fill=(180, 190, 200))
    draw.text((40, 186), datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M:%S"), fill=(180, 190, 200))

    center_x, center_y = 640, 280
    draw.ellipse((center_x - 70, center_y - 70, center_x + 70, center_y + 70), outline=accent, width=4)
    draw.line((center_x - 120, center_y, center_x + 120, center_y), fill=accent, width=3)
    draw.line((center_x, center_y - 120, center_x, center_y + 120), fill=accent, width=3)
    draw.text((560, 430), "Snapshot simulado", fill=(220, 230, 240))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


@app.get("/")
async def root() -> dict[str, str]:
    return FileResponse(PUBLIC_DIR / "fallback.html")


@app.get("/ui")
async def ui() -> FileResponse:
    return FileResponse(PUBLIC_DIR / "fallback.html")


@app.get("/health")
async def health() -> dict[str, int | str]:
    return {"status": "ok", "module": "xSeguranca", "cameras": len(CAMERAS)}


@app.get("/api/cameras")
async def list_cameras() -> dict[str, list[dict[str, object]]]:
    return {
        "cameras": [
            {
                **camera.model_dump(),
                "status": "online",
            }
            for camera in CAMERAS
        ]
    }


@app.get("/api/cameras/{camera_id}/snapshot")
async def camera_snapshot(camera_id: str) -> Response:
    camera = _camera_or_404(camera_id)
    if not camera:
        return JSONResponse(status_code=404, content={"detail": "Camera nao encontrada"})
    return Response(content=_render_snapshot(camera), media_type="image/jpeg")


@app.get("/api/detections/{camera_id}")
async def detections(camera_id: str, limit: int = 20) -> dict[str, object]:
    camera = _camera_or_404(camera_id)
    if not camera:
        return JSONResponse(status_code=404, content={"detail": "Camera nao encontrada"})
    sample_type = "person" if camera.thermal else "movement"
    items = [
        {
            "camera_id": camera.id,
            "camera_name": camera.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detections": [{"type": sample_type, "confidence": 92}],
        }
    ]
    return {"items": items[:limit]}


@app.post("/api/ptz/{camera_id}/command")
async def ptz_command(camera_id: str, command: PTZCommand) -> dict[str, object]:
    camera = _camera_or_404(camera_id)
    if not camera:
        return JSONResponse(status_code=404, content={"detail": "Camera nao encontrada"})
    state = PTZ_STATE[camera.id]
    state["pan"] += command.pan
    state["tilt"] += command.tilt
    state["zoom"] += command.zoom
    return {"status": "ok", "camera_id": camera_id, "state": state, "duration_ms": command.duration_ms}


@app.post("/api/ptz/{camera_id}/preset/{preset_id}/go")
async def ptz_preset_go(camera_id: str, preset_id: int) -> dict[str, object]:
    if not _camera_or_404(camera_id):
        return JSONResponse(status_code=404, content={"detail": "Camera nao encontrada"})
    return {"status": "ok", "camera_id": camera_id, "preset": preset_id, "action": "go"}


@app.post("/api/ptz/{camera_id}/preset/{preset_id}/save")
async def ptz_preset_save(camera_id: str, preset_id: int) -> dict[str, object]:
    if not _camera_or_404(camera_id):
        return JSONResponse(status_code=404, content={"detail": "Camera nao encontrada"})
    return {"status": "ok", "camera_id": camera_id, "preset": preset_id, "action": "save"}


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = {
                "type": "detection",
                "data": {
                    "camera_id": CAMERAS[0].id,
                    "camera_name": CAMERAS[0].name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "detections": [{"type": "movement", "movement_percent": 12.5}],
                },
            }
            await websocket.send_json(payload)
            await asyncio.sleep(15)
    except WebSocketDisconnect:
        return
