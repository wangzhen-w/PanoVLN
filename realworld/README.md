# PanoVLN real-world deployment

[Back to PanoVLN](../README.md) · [Model Zoo](../README.md#model-zoo) · [Configuration and API reference](panovln/README.md)

Run PanoVLN on a Unitree Go2 with a panoramic RGB camera and a remote GPU server. **[PanoVLN_realworld](https://huggingface.co/wangzhen-w/PanoVLN_realworld)** is the dedicated deployment checkpoint, with enhanced trajectory recovery and collision avoidance: it helps the robot regain the instructed route after deviations and navigate around obstacles during physical execution.

The GPU server predicts actions from the instruction and current/history panoramas. The robot client selects observations, applies confidence-guided execution, sends motion commands, and records the trial. The learned policy supplies recovery and avoidance behavior; the controller handles motion execution and stopping. See [how these components work together](panovln/README.md#recovery-avoidance-and-control).

## 1. Hardware and network

The paper setup uses a **Unitree Go2**, an **Insta360 X5 mounted 1.5 m above ground**, and a remote **RTX 3090**. PanoVLN uses approximately **12 GB of GPU memory** in that setup. Treat this as a measured reference configuration when choosing hardware. The robot-side client does not need model weights or PyTorch.

| Component | Required connection |
| --- | --- |
| GPU server | Model environment, checkpoint files, and a TCP port reachable by the robot; default port `8000` |
| Robot computer | ROS2 Foxy, Unitree sport API bridge, FFmpeg, and client Python dependencies |
| Panoramic camera | A stitched equirectangular RGB stream close to 2:1; USB device/index or an OpenCV-readable stream URL |
| Robot ROS network | `/api/sport/request`, `/api/sport/response`, and `/sportmodestate` visible to the client |

Use the GPU server's reachable LAN address in the client configuration. `127.0.0.1` works only when both processes run on the same computer. The ROS bridge and client must use the same robot ROS network/domain; the inference server communicates over HTTP and does not join ROS. The included ROS workspace provides message definitions, so the robot's sport API bridge must already be running.

## 2. Prepare and start the GPU server

Install the [PanoVLN model environment](../README.md#getting-started), download the complete [real-world checkpoint](https://huggingface.co/wangzhen-w/PanoVLN_realworld), and place it in `checkpoints/PanoVLN_realworld/`. Run all commands from the repository root on the indicated machine.

```bash
python -m pip install -r realworld/panovln/requirements.txt
```

Edit the variables at the top of [`panovln/run_server.sh`](panovln/run_server.sh):

```bash
MODEL_PATH="./checkpoints/PanoVLN_realworld"
GPU_IDS="0"
HOST="0.0.0.0"
PORT="8000"
PYTHON_BIN="python3"
LOG_ROOT="./outputs/realworld_server/panovln"
```

Start the server in the model environment:

```bash
bash realworld/panovln/run_server.sh
```

The launcher uses the active environment's `python3`; change `PYTHON_BIN` to select another interpreter. It loads the model before opening the HTTP service. Checkpoint files are not downloaded by the launcher. Relative paths resolve from the repository root, and extra CLI arguments are forwarded to the server.

PanoVGGT weights saved inside the navigation checkpoint take priority over external paths, including paths retained in `config.json`. Leave `PANOVGGT_CHECKPOINT` empty for a complete checkpoint. If the navigation checkpoint has no encoder weights, set `PANOVGGT_CHECKPOINT="./checkpoints/PanoVGGT/model.pt"`. Incompatible saved encoder weights raise an error. `ATTN_IMPLEMENTATION` defaults to `flash_attention_2`; select `sdpa` if that is the attention backend installed in your model environment.

## 3. Prepare the robot computer

Install FFmpeg and the client dependencies into the interpreter used by the launcher, `/usr/bin/python3` by default:

```bash
sudo apt-get install ffmpeg
/usr/bin/python3 -m pip install -r realworld/panovln/requirements-client.txt
```

For a different ROS-compatible Python, set `PYTHON_BIN` in [`panovln/run_go2_client.sh`](panovln/run_go2_client.sh). Build the included ROS message workspace once:

```bash
source /opt/ros/foxy/setup.bash
cd realworld/panovln/ros2_unitree_api_ws
colcon build --base-paths src --packages-select unitree_api unitree_go
cd ../../..
```

Keep the generated `install/` directory on the robot: the launcher sources it automatically. Rebuild after removing it. Check the existing robot bridge without sending any motion commands:

```bash
source /opt/ros/foxy/setup.bash
source realworld/panovln/ros2_unitree_api_ws/install/setup.bash
ros2 topic info /api/sport/request
ros2 topic info /api/sport/response
ros2 topic info /sportmodestate
```

## 4. Configure and inspect a trial

Copy the supplied YAML and edit the copy:

```bash
cp realworld/panovln/go2_client.yaml realworld/panovln/go2_client.local.yaml
```

Set the server address, camera, instruction, and experiment identifiers. Retain the remaining settings in the supplied file:

```yaml
server:
  server_base_url: "http://YOUR_SERVER_IP:8000"

experiment:
  method_name: "PanoVLN"
  scene_name: "office"
  route_id: 1
  trial_id: 1

navigation:
  instruction: "Walk along the hallway and stop at the doorway."
  actions_per_replan: uncertainty
  execution_mode: continuous

robot:
  control_backend: ros2
  real_robot_ack: "yes"

camera:
  camera: "/dev/video0"
  frame_width: 2880
  frame_height: 1440

recording:
  save_output_dir: "./outputs/realworld"
```

The camera can also be an index such as `"0"`, or an RTSP URL such as `"rtsp://CAMERA_IP/stream"` when the camera and OpenCV backend provide that stream. Configure stitching on the camera side; the client expects an already stitched panorama. Resolution and FPS settings are requests to the capture backend; check the actual values printed at startup. See the [camera and recording reference](panovln/README.md#camera-upload-and-recording) for the separate capture, upload, and video resolutions.

Inspect the resolved configuration as JSON without opening the camera, contacting the server, or controlling the robot:

```bash
bash realworld/panovln/run_go2_client.sh \
  --config realworld/panovln/go2_client.local.yaml --print-config
```

Explicit CLI options override YAML values. The supplied YAML selects `ros2` and acknowledges physical execution. A `dry-run` override prints motion commands while still using the camera and model server; `--print-config` is the hardware-free inspection command.

## 5. Run and stop navigation

From the robot computer, confirm that the model server has finished loading:

```bash
curl --fail http://YOUR_SERVER_IP:8000/ready
```

The response should report `model_loaded: true`, `view_mode: "panorama"`, `action_sequence_length: 18`, and `supports_action_uncertainty: true`. With the camera, sport API, and odometry available, start the client:

```bash
bash realworld/panovln/run_go2_client.sh \
  --config realworld/panovln/go2_client.local.yaml
```

The default trial uploads at most 10 historical panoramas plus the current observation at 1280×640. It executes a confidence-selected prefix of each prediction before requesting the next plan. In `continuous` mode, adjacent identical actions are merged, with observations at each 25 cm / 15° action boundary. Prefetch is disabled in the supplied configuration, matching synchronous execution in the paper.

The model's `stop` ends the trial. Press **Ctrl+C in the robot client terminal** to interrupt: cleanup sends zero velocity three times before closing ROS and saving outputs. Exceptions also enter this cleanup path. Keep the robot's own stop control available during physical trials; learned avoidance and client cleanup do not guarantee collision-free execution. The client does not enable or configure a vendor obstacle-avoidance mode.

The controller uses `/sportmodestate` for closed-loop distance and angle control. If odometry is unavailable at action start, it logs a warning and falls back to timed open-loop execution. Review this behavior and motion speeds for your platform; [control parameters and fallback details](panovln/README.md#motion-control-and-stopping) describe the implementation.

For another trial, change the instruction and experiment identifiers, then restart the client. Existing trial directories are not overwritten, so use a new `trial_id` for each repetition. The inference server can remain running; stop the client first, then press Ctrl+C in the server terminal when finished.

## 6. Inspect and reproduce results

The example configuration writes:

```text
outputs/realworld/PanoVLN_office_1_1/
├── navigation.mp4
├── navigation.json
├── summary.json
└── images/            # only with save_contents: all or images
```

`navigation.json` records the instruction, model path, executed actions, request timings, and termination reason. `summary.json` contains trial time, odometry-derived speed, waiting percentage, policy calls, and latency. Success (`sr`), final goal distance (`ne`), and pause counts require annotation/aggregation; these fields are initially `null`. Annotate SR and NE from the actual trial, and use the paper's stationary interval threshold of more than one second when producing pause statistics. See the [logging reference](panovln/README.md#outputs-and-metric-definitions) before comparing methods.

Set `recording.save_contents: all` to preserve sampled observation JPEGs. Save the resolved configuration for each experiment using `--print-config`; the compact navigation log stores the main execution settings, while the YAML records the full camera/network/controller setup.

Each server launch creates `outputs/realworld_server/panovln/<timestamp>_<suffix>/` with `server.log` and `inference.jsonl`. UUID request IDs connect server timings to `navigation.json` entries. See the [HTTP interface](panovln/README.md#http-interface) to call the model with saved images before integrating another robot.

## Baseline deployments

JanusVLN, NaVid, NaVILA, and StreamVLN use the same `run_server.sh` / `run_go2_client.sh` layout in their own directories. Select matching client/server directories, install that method's dependencies, and obtain its upstream checkpoint. Run each method in its own server process.

For these perspective baselines, the client projects the camera panorama using `camera.perspective_*` in its YAML. Uploads, saved observations, and `navigation.mp4` use that perspective view. Keep `upload_image_mode: raw` and the supplied perspective video dimensions. PanoVLN uses panoramic observations and video. When comparing methods, use the same instruction/route identifiers, repeated trials, and annotation rules.

## Further reference

- [PanoVLN settings, HTTP payloads, recovery/avoidance, and troubleshooting](panovln/README.md)
- [Model and training reproduction](../docs/reproduction.md)
- CLI reference: `bash realworld/panovln/run_server.sh --help` and `bash realworld/panovln/run_go2_client.sh --help`
