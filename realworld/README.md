# PanoVLN real-world deployment

[Back to PanoVLN](../README.md) · [Model Zoo](../README.md#model-zoo)

This guide runs PanoVLN on a Unitree Go2 with a panoramic camera. The GPU server performs model inference; the robot client captures observations, selects history, executes actions, and records each trial. Run the commands below from the repository root on the corresponding machine.

After the one-time setup, start `realworld/panovln/run_server.sh` on the GPU server and `realworld/panovln/run_go2_client.sh` on the robot. Wait for the server to be ready before launching the client.

## 1. Prepare the GPU server

Install the [PanoVLN model environment](../README.md#getting-started) and obtain the deployment checkpoint listed in the [Model Zoo](../README.md#model-zoo). In that environment, install the additional HTTP dependencies:

```bash
python -m pip install -r realworld/panovln/requirements.txt
```

Use **`PanoVLN_realworld`**, our dedicated deployment checkpoint with enhanced trajectory recovery and collision avoidance. These capabilities help the robot recover from route deviations and avoid obstacles during physical execution. See the [Model Zoo](../README.md#model-zoo) for checkpoint selection.

Edit the settings at the top of [`panovln/run_server.sh`](panovln/run_server.sh) before launching. The default checkpoint directory is `./checkpoints/PanoVLN_realworld`; weights are not included or downloaded by the launcher. For example, set these variables directly in the script:

```bash
MODEL_PATH="./checkpoints/PanoVLN_realworld"
GPU_IDS="0"
HOST="0.0.0.0"
PORT="8000"
PYTHON_BIN="python3"
LOG_ROOT="./outputs/realworld_server/panovln"
```

Then start the server:

```bash
bash realworld/panovln/run_server.sh
```

PanoVGGT weights saved inside the navigation checkpoint take priority over external paths, including paths retained in `config.json`. Leave `PANOVGGT_CHECKPOINT` empty for a complete checkpoint. Only if the navigation checkpoint has no PanoVGGT encoder weights, set `PANOVGGT_CHECKPOINT="./checkpoints/PanoVGGT/model.pt"` in the same script. Incompatible saved encoder weights raise an error instead of silently falling back to external initialization weights.

The server uses the active environment's `python3` by default. Change `PYTHON_BIN` in the script to select a specific interpreter. Extra command-line arguments are forwarded to the server. Relative paths resolve from the repository root.

## 2. Prepare the robot

The client uses **ROS2 Foxy** and `/usr/bin/python3` by default. Install FFmpeg and the client dependencies on the robot. The robot does not need model weights or PyTorch.

```bash
/usr/bin/python3 -m pip install -r realworld/panovln/requirements-client.txt
```

If using a different ROS-compatible Python, install the dependencies into that interpreter and set `PYTHON_BIN` directly in [`panovln/run_go2_client.sh`](panovln/run_go2_client.sh).

Ensure the Unitree sport API and odometry topics are available, then build the included ROS messages once on the robot:

```bash
source /opt/ros/foxy/setup.bash
cd realworld/panovln/ros2_unitree_api_ws
colcon build --base-paths src --packages-select unitree_api unitree_go
cd ../../..
```

The repository keeps `src/`, which contains the message definitions and build files. Compilation generates `build/` (intermediate files) and `install/` (runtime packages and environment scripts). Keep `install/` on the robot: the client launcher sources it automatically. If it is removed, rebuild before launching.

## 3. Configure a trial

Edit [`panovln/go2_client.yaml`](panovln/go2_client.yaml). Set the server address, camera device, navigation instruction, and experiment identifiers. The following is an excerpt; retain the other settings in the supplied file:

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

Use the GPU server's reachable address. `127.0.0.1` only works when the client and server run on the same machine. Match the camera settings to your panoramic camera and review the `motion` and `odometry` settings for your robot.

The supplied PanoVLN configuration uploads up to 10 historical panoramas plus the current observation, resized to 1280×640. The client selects history and uses the returned uncertainty to determine how many actions to execute before replanning. In `continuous` mode, adjacent identical actions are merged while observations are captured after each 25 cm / 15° action unit.

Inspect the resolved configuration without opening the camera or controlling the robot:

```bash
bash realworld/panovln/run_go2_client.sh --print-config
```

## 4. Run navigation

With the model server running, check its readiness from the robot:

```bash
curl --fail http://YOUR_SERVER_IP:8000/ready
```

After this succeeds, start the client on the robot:

```bash
bash realworld/panovln/run_go2_client.sh
```

The client handles `Ctrl+C` by sending a stop command and closing its recording outputs. For another trial, update the instruction and experiment identifiers as needed, then restart the client. Existing trial directories are not overwritten; use a new `trial_id` for each repetition. The server can remain running between trials.

The other method directories use the same `run_server.sh` / `run_go2_client.sh` workflow with their own dependencies, weight settings, and client YAML. Select the matching directory for both processes and install its `requirements.txt`. JanusVLN, NaVid, NaVILA, and StreamVLN support the same Python 3.12 / PyTorch 2.10.0 / Transformers 5.5.0 environment as PanoVLN. Run each method in its own server process. Refer to the methods' upstream repositories for checkpoint details.

For these four perspective baselines, the client projects each panoramic camera frame using `camera.perspective_*` in its YAML. Uploads, saved images, and `navigation.mp4` all use that perspective view; the server receives perspective images and applies the model's own preprocessing. Keep `upload_image_mode: raw` and use the supplied perspective video dimensions. Update both client and server together and restart them when switching from the older server-side projection workflow. PanoVLN continues to use panoramic observations and video.

## 5. Inspect the results

With the example configuration above, the client writes:

```text
outputs/realworld/PanoVLN_office_1_1/
├── navigation.mp4
├── navigation.json
└── summary.json
```

`navigation.json` records the instruction, executed actions, and request timings. `summary.json` contains navigation efficiency metrics and fields for manually annotated success (`sr`) and final distance to the goal (`ne`). Set `recording.save_contents: all` to also save observation images.

Each server launch creates `outputs/realworld_server/panovln/<timestamp>_<suffix>/`, containing `server.log` and `inference.jsonl`. Request IDs connect server timings to the client records. Edit `LOG_ROOT` in `panovln/run_server.sh` to change the server log location.

For available server and client options:

```bash
bash realworld/panovln/run_server.sh --help
bash realworld/panovln/run_go2_client.sh --help
```
