# PanoVLN robot client and inference API

[Deployment walkthrough](../README.md) · [Model Zoo](../../README.md#model-zoo) · [Real-world checkpoint](https://huggingface.co/wangzhen-w/PanoVLN_realworld)

This directory connects the PanoVLN policy to a Unitree Go2. [`server.py`](server.py) loads the checkpoint on a GPU computer and exposes HTTP inference. [`go2_client.py`](go2_client.py) runs beside the robot, captures panoramas, applies the execution policy, and controls the robot over ROS2.

## Recovery, avoidance, and control

**PanoVLN_realworld strengthens trajectory recovery and collision avoidance for robot deployment.** Its learned policy uses the instruction, panoramic context, and observation history to recover route progress after deviations and choose actions around obstacles. Use this checkpoint for physical navigation.

Three components contribute different behavior:

| Component | Role | Implementation |
| --- | --- | --- |
| Learned navigation policy | Instruction following, route recovery, and obstacle-aware action selection | [`inference.py`](inference.py) and the real-world checkpoint |
| Confidence-guided execution | Selects how many predicted actions to execute before observing and replanning | [`src/eval/action_policy.py`](../../src/eval/action_policy.py), shared with the robot client |
| Robot controller | Executes bounded forward/turn primitives, tracks odometry when available, and sends zero velocity on stop/cleanup | [`Ros2SportBackend` in `go2_client.py`](go2_client.py) |

The public [DAgger collector](../../src/data/generate_dagger_data.py) mixes model and oracle execution and records oracle action sequences at visited decision states. [Training-data preparation](../../src/data/prepare_training_data.py) pairs those corrective targets with the actually executed observation history. This provides a reproducible mechanism for training on policy-induced deviations. The complete checkpoint-specific training mixture and additional recovery/avoidance data recipe have not yet been documented, so the public DAgger settings alone should not be treated as an exact reconstruction of `PanoVLN_realworld`.

[`src/eval/collision_recovery.py`](../../src/eval/collision_recovery.py) is a separate **simulation evaluation** rule that reacts to simulator collision feedback and static RGB. The robot client does not call that rule. Its ROS controller does not inspect the `range_obstacle` field or enable a vendor collision-avoidance API.

## Configuration precedence

The launcher reads [`go2_client.yaml`](go2_client.yaml). `--config path/to/trial.yaml` selects another file; explicit CLI flags override YAML. Configuration is grouped YAML, while `--print-config` emits resolved JSON:

```bash
bash realworld/panovln/run_go2_client.sh \
  --config realworld/panovln/go2_client.yaml \
  --control-backend dry-run --real-robot-ack no --print-config
```

This command exits before camera access, HTTP calls, or ROS initialization. A normal run with `--control-backend dry-run` still captures images and requests model predictions; it replaces motion with printed commands.

Keys shown below are YAML names; their CLI equivalents replace underscores with hyphens, for example `uncertainty_budget` → `--uncertainty-budget`. The tables list the supplied YAML values, which may differ from the Python CLI defaults when no YAML is supplied.

### Navigation and history

| Setting | Supplied value | Meaning |
| --- | --- | --- |
| `instruction` / `instruction_file` | Text / `null` | A nonempty file path takes priority over inline instruction text |
| `max_replans` | `100` | Maximum planning rounds; `0` allows unlimited rounds |
| `actions_per_replan` | `uncertainty` | Adaptive prefix length; positive integer fixes the count; `0` uses the sequence length advertised by `/ready` |
| `uncertainty_budget` | `1.2` | Budget for cumulative `−log p(action)` in adaptive execution |
| `replan_action_range` | `[4, 8]` | Inclusive nominal atom count range for the adaptive prefix |
| `stop_commit_max_actions` | `12` | A predicted STOP within this window takes priority over the nominal budget/range; `0` disables this override |
| `execution_mode` | `continuous` | Merge adjacent identical actions and capture at atom boundaries; `atomic` stops and settles at each atom |
| `prefetch_after_actions` | `0` | Synchronous execution; a positive value starts another prediction early at a merged-action boundary |
| `history_limit` | `120` | Maximum stored observation JPEGs in client memory |
| `upload_memory_pool_window_frames` | `100` | Recent history window used for uniform memory selection |
| `upload_max_memory_images` | `10` | Maximum selected historical images, in addition to the current image |
| `request_timeout` | `180` seconds (CLI default) | Per-request HTTP timeout; can be added under `server` |

The uncertainty budget measures model action confidence, not a calibrated probability of collision. The nominal minimum prefix can exceed that budget, and STOP/short predictions may reduce the actual executed sequence. Keep the supplied settings for the default deployment behavior.

### Camera, upload, and recording

| Stage | Supplied setting | What it controls |
| --- | --- | --- |
| Capture | `camera: "/dev/video0"`, `frame_width: 2880`, `frame_height: 1440`, `camera_fps: 30` | Requested camera properties; actual backend values are printed at startup |
| JPEG observations | `jpeg_quality: 90`, `capture_flush_frames: 2` | JPEG encoding and stale-frame flushing before an observation |
| Model upload | `upload_image_mode: resize`, `upload_width: 1280`, `upload_height: 640` | Resolution of images sent to the server; `raw` preserves the captured JPEG dimensions |
| Recorded video | `video_width: 1280`, `video_height: 640`, `video_fps: 10` | Video output, independently configured from upload dimensions |
| Video writer | `video_writer: ffmpeg`, `video_codec: libx264` | FFmpeg H.264 recording; FFmpeg must be on `PATH` |
| Saved files | `save_contents: video,json` | `images`, `video`, `json`, comma-separated combinations, `all`, or `none` |

`camera` accepts an OpenCV index, device path, or stream URL. Example for an RTSP camera delivering an already stitched panorama:

```yaml
camera:
  camera: "rtsp://CAMERA_IP/stream"
  camera_fourcc: ""
  frame_width: 2880
  frame_height: 1440
  camera_fps: 30
```

`camera_fourcc: ""` leaves codec selection to the stream backend. RTSP decoding depends on the local OpenCV/FFmpeg build; the client passes the URL directly to OpenCV. Network streams may ignore requested capture dimensions/FPS, so configure the camera's output itself and check the startup report. The client performs no dual-fisheye stitching.

For sharper recording assets, increase `video_width`/`video_height` up to the actual camera output and choose an appropriate `video_fps`; raising only these values cannot recover detail already absent from the capture. `save_contents: all` preserves observation JPEGs before upload resizing, useful for inspecting source quality. Those JPEGs are selected observation samples, not every camera/video frame.

### Motion control and stopping

| Setting | Supplied value | Meaning |
| --- | --- | --- |
| `control_backend` / `real_robot_ack` | `ros2` / `"yes"` | Physical robot backend and explicit runtime acknowledgement; quote `yes` in YAML |
| `forward_distance` / `forward_speed` | `0.25 m` / `0.35 m/s` | Forward atom distance and velocity bound |
| `turn_degrees` / `yaw_speed` | `15°` / `0.8 rad/s` | Turn atom angle and angular velocity bound |
| `command_period` | `0.05 s` | Velocity command interval |
| `settle_time` / `post_capture_settle_time` | `0.1 s` / `0.05 s` | Settling around stopped capture; in continuous mode this applies at merged-group boundaries |
| `disable_odom_control` | `false` | Use odometry feedback when available; `true` selects timed open-loop motion |
| `odom_timeout` | `1.0 s` | Initial wait for usable odometry at an action's start |
| `forward_tolerance` / `turn_tolerance_degrees` | `0.04 m` / `3°` | Closed-loop completion tolerances |
| `forward_kp`, `forward_kd` | `3.0`, `0.0` | Forward proportional/derivative gains |
| `turn_kp`, `turn_kd` | `3.0`, `0.0` | Yaw proportional/derivative gains |
| `min_forward_speed` / `min_yaw_speed` | `0.15 m/s` / `0.35 rad/s` | Minimum nonzero controller commands |

The ROS backend publishes to `/api/sport/request`, reads `/api/sport/response`, and subscribes to `/sportmodestate`. It uses sport API `1002` for balance stand and `1008` for velocity commands. STOP is a zero-velocity command. Normal termination, Ctrl+C, SIGTERM, and handled exceptions enter cleanup, which sends zero velocity three times before destroying the ROS node.

When odometry is unavailable at action start, the controller logs an open-loop fallback and uses motion duration computed from distance/speed or angle/angular speed. If odometry stops updating during a closed-loop segment, that segment exits and sends zero velocity; subsequent actions can again fall back to open loop.

## HTTP interface

[`run_server.sh`](run_server.sh) sets the checkpoint, CUDA device visibility, bind address, attention backend, and log directory. Configure these variables in the script; they are ordinary assignments, so prefixing an environment variable does not override them. The server accepts these CLI flags:

```text
--host --port --model-path --panovggt-checkpoint
--attn-implementation --reload --log-dir
```

The model loads before HTTP service starts. `/ready` and `/health` report the loaded model, 18-action horizon, panoramic view mode, and uncertainty support. Calls use a model lock so concurrent requests share one model instance sequentially.

| Endpoint | Input | Output |
| --- | --- | --- |
| `GET /ready`, `GET /health` | None | Readiness and model metadata |
| `POST /predict` | Multipart `instruction` plus one or more `images` files | Actions and timings |
| `POST /predict_json` | JSON with `instruction`, ordered base64 `images`, and optional uncertainty options | Same prediction response |

Images must be ordered from oldest to newest; the last image is current. These requests run inference only and send no robot motion commands. Example with a saved current panorama:

```bash
curl --fail http://YOUR_SERVER_IP:8000/predict \
  -F 'instruction=Walk forward and stop at the doorway.' \
  -F 'images=@frame.jpg' \
  -F 'include_uncertainty=true' \
  -F 'uncertainty_max_actions=8'
```

The JSON endpoint accepts the same image bytes encoded as base64 strings. Build a valid payload from a saved image:

```bash
python - <<'PY'
import base64
import json
from pathlib import Path
payload = {
    "instruction": "Walk forward and stop at the doorway.",
    "images": [base64.b64encode(Path("frame.jpg").read_bytes()).decode("ascii")],
    "include_uncertainty": True,
    "uncertainty_max_actions": 8,
}
Path("request.json").write_text(json.dumps(payload))
PY
curl --fail http://YOUR_SERVER_IP:8000/predict_json \
  -H 'Content-Type: application/json' --data-binary @request.json
```

Predictions include `actions`, `executable_actions`, `raw_text`, `prompt_images`, `latency_s`, optional `uncertainty_actions`/`action_uncertainties`, `inference_s`, `server_s`, and a UUID `request_id`. The client executes only `stop`, `forward`, `left`, and `right`; the queue ends at the first STOP. `X-Request-ID` connects a request to the server log and is also returned in the response.

## Outputs and metric definitions

`experiment.method_name`, `scene_name`, `route_id`, and `trial_id` form the directory name. Existing directories are rejected to preserve completed trials. Defaults with missing labels become `null`; fill all labels for reproducible comparisons.

| File | Contents |
| --- | --- |
| `navigation.mp4` | Continuous camera recording at configured video resolution/FPS |
| `images/*.jpg` | Optional initial and action-boundary observations at capture JPEG resolution |
| `navigation.json` | Trial identity, instruction, model path, execution settings, stop/failure reason, and per-call predictions/executed actions |
| `summary.json` | Aggregate efficiency fields and initially empty SR/NE/pause annotations |
| Server `server.log` | Startup and per-request console log |
| Server `inference.jsonl` | Request UUID, endpoint, image count, queue time, server time, inference time, actions, and status/error |

The trial clock begins with the first inference request and ends when navigation terminates. `summary.json` uses seconds for `time_s`/`latency_s`, metres for `ne`, and **metres per second** for `speed_mps`; multiply the latter by 100 when reporting cm/s. Time and speed include policy waiting. Distance and speed use observed odometry; insufficient odometry produces `null`, rather than zero speed. `calls` counts policy requests. Client latency includes the request round trip; `server_s` includes queue/processing time after request upload, and `inference_s` isolates the model's measured inference stage.

The saved SR/NE fields require manual trial labels. Record success as `1`/`0` and final distance in metres, using a consistent goal criterion across all methods. The current logger leaves `pauses` unset; compute and document pause counts from stationary intervals when recreating the paper's more-than-one-second threshold. For pause statistics, retain a timestamped odometry recording or annotate the recorded video. The compact JSON does not retain the full odometry trace. Per-call `wait_s` is available in `navigation.json`, but one policy wait is not automatically one complete stationary interval.

For comparisons, retain the original YAML (or its resolved JSON), checkpoint revision, route/instruction, trial ID, motion and execution parameters, camera settings, and annotated outcomes. The paper evaluates 20 shared instruction–route pairs per environment without scene-specific fine-tuning; a single demonstration video does not reproduce that evaluation.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Connection refused at `/ready` | Model startup log, server IP/bind address/port, firewall; the endpoint opens only after model loading |
| Model lacks uncertainty support | Use matching PanoVLN client/server versions and restart the server |
| Camera cannot open or has the wrong shape | Device/index/RTSP URL, camera permissions, OpenCV stream backend, camera-side 2:1 stitching |
| ROS workspace missing | Build `unitree_api` and `unitree_go`, then retain/source the generated `install/setup.bash` |
| No sport response or no odometry | Robot bridge, ROS domain/network, and the three topic names above; missing initial odometry triggers timed fallback |
| Trial directory already exists | Choose a new `trial_id` |
| `ffmpeg` missing | Install FFmpeg on the robot computer or configure a working OpenCV writer/codec |
| Encoder checkpoint error | Check the complete navigation checkpoint first; use an external PanoVGGT path only when saved encoder weights are absent |

Configuration and help can be validated without loading weights or touching hardware:

```bash
bash realworld/panovln/run_server.sh --help
bash realworld/panovln/run_go2_client.sh --help
bash realworld/panovln/run_go2_client.sh --print-config
```
