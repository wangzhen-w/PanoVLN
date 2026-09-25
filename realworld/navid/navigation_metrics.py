"""Client-side trial measurements for the paper's real-world efficiency table.

All event timestamps are monotonic seconds since collector creation. Requests may
finish on a prefetch thread; the final snapshot is clipped to trial termination.
No robot commands, image selection, or navigation policy live here.
"""
from __future__ import annotations

import copy
import math
import threading
import time


class NavigationMetrics:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._origin = clock()
        self._lock = threading.RLock()
        self.started_t_s = None
        self.ended_t_s = None
        self.requests = []
        self.wait_intervals = []
        self.motion_intervals = []
        self.trajectory = []
        self._latest_odom = None
        self._waiting = None

    def now(self):
        return self._clock() - self._origin

    def begin_request(self, *, source, image_count, upload_bytes, server_request_id=None):
        with self._lock:
            if self.ended_t_s is not None:
                raise RuntimeError("Navigation has terminated; no new policy request is allowed")
            now = self.now()
            if self.started_t_s is None:
                self.started_t_s = now
                if self._latest_odom is not None:
                    self.trajectory.append({**self._latest_odom, "baseline": True})
            request_id = len(self.requests) + 1
            self.requests.append({
                "request_id": request_id, "source": source,
                "started_t_s": now, "ended_t_s": None, "status": "pending",
                "image_count": image_count, "upload_bytes": upload_bytes,
                "latency_s": None, "server_latency_s": None, "error": None,
                "server_request_id": server_request_id,
                "server_s": None, "inference_s": None, "transport_overhead_s": None,
            })
            return request_id

    def end_request(self, request_id, *, error=None, server_latency_s=None,
                    server_s=None, inference_s=None):
        with self._lock:
            row = self.requests[request_id - 1]
            row["ended_t_s"] = self.now()
            row["status"] = ("interrupted" if isinstance(error, KeyboardInterrupt)
                             else "failed" if error is not None else "succeeded")
            row["latency_s"] = row["ended_t_s"] - row["started_t_s"]
            row["server_latency_s"] = server_latency_s
            for key, value in (("server_s", server_s), ("inference_s", inference_s)):
                if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                    row[key] = value
            if row["server_s"] is not None and row["latency_s"] >= row["server_s"]:
                # Includes HTTP transfer, form serialization/parsing and framework
                # overhead. Durations need no clock sync; this is NOT pure RTT.
                row["transport_overhead_s"] = row["latency_s"] - row["server_s"]
            row["error"] = repr(error) if error is not None else None

    def begin_wait(self):
        with self._lock:
            self._waiting = {"started_t_s": self.now()}

    def end_wait(self, request_id=None, *, at=None):
        with self._lock:
            if self._waiting is None:
                return
            end = self.now() if at is None else at
            if request_id is not None:
                received = self.requests[request_id - 1]["ended_t_s"]
                if received is not None:
                    end = min(end, received)
            if self.started_t_s is not None:
                start = max(self.started_t_s, self._waiting["started_t_s"])
                # A prefetched result received before this wait contributes zero.
                if end > start:
                    self.wait_intervals.append({
                        **self._waiting, "started_t_s": start, "ended_t_s": end,
                        "duration_s": end - start, "request_id": request_id,
                    })
            self._waiting = None

    def begin_motion(self):
        with self._lock:
            row = {"started_t_s": self.now(), "ended_t_s": None}
            self.motion_intervals.append(row)
            return row

    def end_motion(self, row):
        with self._lock:
            row["ended_t_s"] = self.now()

    def record_odometry(self, odom):
        """Observe the already decoded sport state; never spin or control ROS."""
        values = (odom.x, odom.y, odom.yaw, odom.forward_speed, odom.yaw_speed, odom.stamp_s)
        if not all(math.isfinite(value) for value in values):
            return
        row = {
            "t_s": odom.stamp_s - self._origin, "x_m": odom.x, "y_m": odom.y,
            "yaw_rad": odom.yaw, "forward_speed_mps": odom.forward_speed,
            "yaw_speed_radps": odom.yaw_speed,
        }
        with self._lock:
            self._latest_odom = row
            if self.started_t_s is not None and self.ended_t_s is None:
                self.trajectory.append(row)

    def finish(self, at):
        with self._lock:
            self.ended_t_s = at
            self.end_wait(at=at)

    def snapshot(self):
        with self._lock:
            end = self.ended_t_s if self.ended_t_s is not None else self.now()
            requests = copy.deepcopy([r for r in self.requests if r["started_t_s"] <= end])
            waits = copy.deepcopy(self.wait_intervals)
            motions = copy.deepcopy(self.motion_intervals)
            trajectory = copy.deepcopy([p for p in self.trajectory if p["t_s"] <= end])
            start = self.started_t_s
        for row in requests:
            if row["ended_t_s"] is None or row["ended_t_s"] > end:
                row.update(status="pending_at_termination", ended_t_s=None, latency_s=None,
                           server_latency_s=None, server_s=None, inference_s=None,
                           transport_overhead_s=None, error=None)
            observed_end = end if row["ended_t_s"] is None else row["ended_t_s"]
            row["observed_duration_s"] = observed_end - row["started_t_s"]
        for row in requests:
            request_end = end if row["ended_t_s"] is None else row["ended_t_s"]
            row["wait_s"] = sum(
                max(0.0, min(request_end, wait["ended_t_s"]) - max(row["started_t_s"], wait["started_t_s"]))
                for wait in waits
            )
        latency = [r["latency_s"] for r in requests if r["status"] == "succeeded"]
        total_time = end - start if start is not None else None
        wait_time = sum(r["wait_s"] for r in requests)
        points = sorted(trajectory, key=lambda row: row["t_s"])
        sampled_distance = sum(math.hypot(b["x_m"] - a["x_m"], b["y_m"] - a["y_m"])
                               for a, b in zip(points, points[1:]))
        missing_motion = 0
        for motion in motions:
            samples = sum(motion["started_t_s"] <= p["t_s"] <= min(motion["ended_t_s"] or end, end)
                          for p in points)
            motion["odometry_samples"] = samples
            if samples < 2:
                missing_motion += 1
        # Preserve partial observations, but never turn missing odometry into a
        # measured zero distance or use commanded forward distance as a proxy.
        distance = sampled_distance if len(points) >= 2 and missing_motion == 0 else None
        return {
            "trial_started_t_s": start,
            "distance_m": distance,
            "distance_status": "odometry_estimate" if distance is not None else "insufficient_odometry",
            "requests": requests,
            "summary": {
                "time_s": total_time,
                "speed_mps": distance / total_time if distance is not None and total_time else None,
                "wait_pct": 100 * wait_time / total_time if total_time else None,
                "pauses": None,  # The user will select a threshold later using calls[].wait_s.
                "calls": len(requests),
                "latency_s": sum(latency) / len(latency) if latency else None,
                "sr": None,  # Manually label this trial: 1 for success, 0 for failure.
                "ne": None,  # Manually measured final distance to goal, in metres.
            },
        }


def build_navigation_reports(run_log, measurements):
    """Return a readable trial log and the paper metrics with manual SR/NE."""
    start = measurements["trial_started_t_s"]
    predictions = {p["request_id"]: p for p in run_log["predictions"] if p.get("request_id") is not None}
    actions_by_replan = {}
    for action in run_log["executed_actions"]:
        actions_by_replan.setdefault(action["replan"], []).append(action)
    calls = []
    for request in measurements["requests"]:
        prediction = predictions.get(request["request_id"])
        call = {
            "id": request["request_id"],
            "start_s": request["started_t_s"] - start,
            "source": request["source"],
            "status": request["status"],
            "latency_s": request["latency_s"],
            "server_request_id": request.get("server_request_id"),
            "server_s": request.get("server_s"),
            "inference_s": request.get("inference_s"),
            "transport_overhead_s": request.get("transport_overhead_s"),
            "wait_s": request["wait_s"],
            "actions": " ".join(prediction["actions"]) if prediction else None,
            "executed": [],
        }
        if prediction:
            call["execution_limit"] = prediction["effective_actions_per_replan"]
            for action in actions_by_replan.get(prediction["replan"], []):
                call["executed"].append({
                    "action": action["action"], "count": action["action_count"],
                    "completed": action["completed_atom_count"], "status": action["status"],
                    "start_s": action["started_t_s"] - start,
                    "duration_s": action["duration_s"],
                })
        if request["error"] is not None:
            call["error"] = request["error"]
        calls.append(call)
    ready = run_log["server_ready"] or {}
    details = {
        "run_id": run_log["run_id"],
        "experiment": run_log["experiment"],
        "instruction": run_log["instruction"],
        "model_path": ready.get("model_path"),
        "server": ready,
        "observation_count": len(run_log["observations"]),
        "started_at": run_log["started_at"],
        "finished_at": run_log["finished_at"],
        "status": run_log["status"],
        "end_reason": run_log["termination_reason"],
        "distance_m": measurements["distance_m"],
        "distance_status": measurements["distance_status"],
        "settings": {
            "execution_mode": run_log["execution_mode"],
            "actions_per_replan": run_log["configured_actions_per_replan"],
            "uncertainty_budget": run_log["uncertainty_budget"],
            "replan_action_range": run_log["replan_action_range"],
            "prefetch_after_actions": run_log["prefetch_after_actions"],
            "forward_distance_m": run_log["motion"]["forward_distance_m"],
            "turn_degrees": run_log["motion"]["turn_degrees"],
        },
        "annotations": {
            "success": None,
            "final_goal_distance_m": None,
            "notes": None,
        },
        "calls": calls,
    }
    if run_log["error"] is not None:
        details["error"] = run_log["error"]
    video = run_log["video_summary"]
    if video and video.get("error"):
        details["video_error"] = video["error"]
    return _round_seconds(details), _round_seconds(measurements["summary"])


def _round_seconds(value):
    # Six decimals retain sub-millisecond waits without printing float noise.
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: _round_seconds(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_round_seconds(item) for item in value]
    return value
