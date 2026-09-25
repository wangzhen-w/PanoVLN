from __future__ import annotations

from src.vln_config import VLN_ACTION_SEQUENCE_LENGTH

import argparse
import base64
import json
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from typing import TYPE_CHECKING
from .config import DEFAULT_MODEL_PATH, InferenceConfig

if TYPE_CHECKING:
    from .inference import PanoVLNPredictor
from src.eval.action_policy import DEFAULT_REPLAN_ACTION_RANGE


def _log_stage(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} [realworld.server] {message}", flush=True)


class PredictionOptions(BaseModel):
    include_uncertainty: bool = False
    uncertainty_max_actions: int = Field(default=DEFAULT_REPLAN_ACTION_RANGE[1], gt=0)


class PredictJsonRequest(PredictionOptions):
    instruction: str
    images: list[str] = Field(
        ...,
        description="Base64-encoded JPEG/PNG images ordered from older to newer.",
    )


def create_app(
    settings: InferenceConfig, predictor: PanoVLNPredictor, *, log_dir: str | Path | None = None,
) -> FastAPI:
    app = FastAPI(title="PanoVLN Real-world Server")
    app.state.settings = settings
    app.state.predictor = predictor
    app.state.model_lock = threading.RLock()
    log_path = Path(log_dir) / "inference.jsonl" if log_dir is not None else None
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.touch(exist_ok=True)

    def run_prediction(request, instruction, images, options, processing_start):
        # Start after the body is received. Thread-pool and model-lock waits are
        # included, without blocking the event loop during model execution.
        try:
            request_id = str(UUID(request.headers.get("X-Request-ID", "")))
        except ValueError:
            request_id = str(uuid4())
        row = {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": request.url.path,
            "images": len(images),
            "status": "succeeded",
            "inference_s": None,
        }
        with app.state.model_lock:
            predict_start = time.perf_counter()
            row["queue_s"] = predict_start - processing_start
            _log_stage(f"request_id={request_id} inference started images={len(images)}")
            try:
                result = app.state.predictor.predict(
                    instruction=instruction, images=images,
                    include_uncertainty=options.include_uncertainty,
                    uncertainty_max_actions=options.uncertainty_max_actions,
                )
                payload = asdict(result)
                row["inference_s"] = result.inference_s
                row["actions"] = result.actions
                status_code = 200
            except Exception as exc:
                row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                payload = {"detail": str(exc)}
                status_code = 500
            completed = time.perf_counter()
            row["predict_s"] = completed - predict_start
            row["server_s"] = completed - processing_start
            row = {key: round(value, 6) if isinstance(value, float) else value
                   for key, value in row.items()}
            # Open/close each line so calls survive an interrupted server run.
            # The model lock also prevents concurrent log lines interleaving.
            if log_path is not None:
                with log_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            _log_stage(f"request_id={request_id} {row['status']} "
                       f"server_s={row['server_s']} inference_s={row['inference_s']}"
                       + (f" error={row['error']}" if "error" in row else ""))
        payload.update(request_id=request_id, server_s=row["server_s"],
                       inference_s=row["inference_s"])
        return JSONResponse(payload, status_code=status_code, headers={"X-Request-ID": request_id})

    @app.get("/health")
    def health():
        return {
            "ok": True,
            "model_loaded": True,
            "model_path": app.state.settings.model_path,
            "action_sequence_length": VLN_ACTION_SEQUENCE_LENGTH,
            "view_mode": "panorama",
            "supports_action_uncertainty": True,
        }

    @app.get("/ready")
    def ready():
        _log_stage("/ready requested")
        return {
            "ok": True,
            "model_loaded": True,
            "model_path": app.state.settings.model_path,
            "action_sequence_length": VLN_ACTION_SEQUENCE_LENGTH,
            "view_mode": "panorama",
            "supports_action_uncertainty": True,
        }

    @app.post("/predict")
    async def predict_multipart(request: Request):
        async with request.form() as form:
            try:
                options = PredictionOptions(
                    include_uncertainty=form.get("include_uncertainty", False),
                    uncertainty_max_actions=form.get("uncertainty_max_actions", DEFAULT_REPLAN_ACTION_RANGE[1]),
                )
            except ValidationError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            instruction = str(form.get("instruction", "")).strip()
            if not instruction:
                raise HTTPException(status_code=400, detail="Missing form field: instruction")

            uploads = []
            for field_name in ("images", "image", "files", "file"):
                uploads.extend(form.getlist(field_name))
            image_bytes = []
            for upload in uploads:
                if hasattr(upload, "read"):
                    image_bytes.append(await upload.read())
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Upload at least one image file")
        return await run_in_threadpool(
            run_prediction, request, instruction, image_bytes, options, time.perf_counter(),
        )

    @app.post("/predict_json")
    async def predict_json(payload: PredictJsonRequest, request: Request):
        if not payload.instruction.strip():
            raise HTTPException(status_code=400, detail="instruction must be non-empty")
        if not payload.images:
            raise HTTPException(status_code=400, detail="images must be non-empty")
        try:
            image_bytes = [base64.b64decode(image) for image in payload.images]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid base64 image") from exc
        return await run_in_threadpool(
            run_prediction, request, payload.instruction, image_bytes, payload, time.perf_counter(),
        )

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve PanoVLN over HTTP.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH)
    parser.add_argument("--panovggt-checkpoint", default=None)
    parser.add_argument("--attn-implementation", default="flash_attention_2")
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--log-dir", default=None, help="Directory for per-call inference.jsonl")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = InferenceConfig(
        model_path=args.model_path,
        panovggt_checkpoint_path=args.panovggt_checkpoint,
        attn_implementation=args.attn_implementation,
    )
    _log_stage(f"server_settings={asdict(settings)}")
    start = time.perf_counter()
    _log_stage("loading model before starting HTTP server")
    from .inference import PanoVLNPredictor
    predictor = PanoVLNPredictor(settings)
    _log_stage(f"model ready in {time.perf_counter() - start:.2f}s; starting HTTP server")
    server_app = create_app(settings, predictor, log_dir=args.log_dir)
    uvicorn.run(server_app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
