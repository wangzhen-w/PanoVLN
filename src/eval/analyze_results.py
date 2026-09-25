import argparse
import json
import math
from pathlib import Path

import numpy as np


TARGET_KEYS = ("success", "spl", "oracle_success", "distance_to_goal", "path_length", "ndtw")
METRIC_DIRECTIONS = {
    "success": "higher",
    "spl": "higher",
    "oracle_success": "higher",
    "distance_to_goal": "lower",
    # Unconditional path length is descriptive: a failed agent that stops
    # immediately can be shorter without being better.
    "path_length": "descriptive",
    "ndtw": "higher",
}
RESULT_FILENAME = "result.jsonl"
RESULT_SUMMARY_FILENAME = "result_summary.json"
PAIRED_COMPARISON_FILENAME = "paired_comparison.json"


def finite_metric_value(value):
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def metric_values(rows, key):
    return [
        value
        for row in rows
        if (value := finite_metric_value(row.get(key))) is not None
    ]


def format_metric(value):
    return f"{value:.3f}" if value is not None else "N/A"


def iter_result_paths(output_path):
    paths = []
    merged_path = output_path / RESULT_FILENAME
    if merged_path.exists():
        paths.append(merged_path)
    paths.extend(sorted(output_path.glob("result_rank*.jsonl")))
    return paths


def reorder_row(row):
    ordered = {}
    for key in ("id", "scene_id"):
        if key in row:
            ordered[key] = row[key]
    for key in TARGET_KEYS:
        if key in row:
            ordered[key] = row[key]
    for key, value in row.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def load_rows(output_path):
    row_map = {}
    for path in iter_result_paths(output_path):
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                episode_id = row.get("id", row.get("episode_id"))
                scene_id = row.get("scene_id")
                if episode_id is None or scene_id is None:
                    continue
                key = (str(scene_id), str(episode_id))
                row["id"] = str(episode_id)
                row["scene_id"] = str(scene_id)
                row_map[key] = reorder_row(row)
    return [row_map[key] for key in sorted(row_map.keys())]


def summarize_rows(rows):
    """Average each metric over its own finite values, retaining valid zeros."""
    summary = {"num_episodes": len(rows)}
    for key in TARGET_KEYS:
        values = metric_values(rows, key)
        summary[key] = float(sum(values) / len(values)) if values else None
    return summary


def write_outputs(output_path, rows, summary):
    merged_path = output_path / RESULT_FILENAME
    with merged_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(reorder_row(row), ensure_ascii=False) + "\n")

    summary_path = output_path / RESULT_SUMMARY_FILENAME
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    for shard_path in sorted(output_path.glob("result_rank*.jsonl")):
        shard_path.unlink()


def _row_key(row):
    return str(row["scene_id"]), str(row["id"])


def paired_bootstrap_comparison(
    baseline_rows,
    candidate_rows,
    *,
    num_samples,
    seed,
):
    baseline_map = {_row_key(row): row for row in baseline_rows}
    candidate_map = {_row_key(row): row for row in candidate_rows}
    paired_keys = sorted(set(baseline_map) & set(candidate_map))
    if not paired_keys:
        raise ValueError("Baseline and candidate have no paired episodes")

    rng = np.random.default_rng(seed)
    metrics = {}
    for metric_name in TARGET_KEYS:
        pairs = []
        for key in paired_keys:
            baseline = finite_metric_value(baseline_map[key].get(metric_name))
            candidate = finite_metric_value(candidate_map[key].get(metric_name))
            if baseline is not None and candidate is not None:
                pairs.append((baseline, candidate))
        if not pairs:
            continue
        values = np.asarray(pairs, dtype=np.float64)
        raw_differences = values[:, 1] - values[:, 0]
        bootstrap_means = np.empty(int(num_samples), dtype=np.float64)
        chunk_size = 256
        for start in range(0, int(num_samples), chunk_size):
            stop = min(start + chunk_size, int(num_samples))
            indices = rng.integers(
                0,
                raw_differences.size,
                size=(stop - start, raw_differences.size),
            )
            bootstrap_means[start:stop] = raw_differences[indices].mean(
                axis=1
            )

        lower, upper = np.quantile(bootstrap_means, [0.025, 0.975])
        direction = METRIC_DIRECTIONS[metric_name]
        if direction == "higher":
            improvement_probability = float(
                (bootstrap_means > 0.0).mean()
            )
        elif direction == "lower":
            improvement_probability = float(
                (bootstrap_means < 0.0).mean()
            )
        else:
            improvement_probability = None
        metrics[metric_name] = {
            "num_paired_episodes": int(raw_differences.size),
            "baseline_mean": float(values[:, 0].mean()),
            "candidate_mean": float(values[:, 1].mean()),
            "candidate_minus_baseline": float(raw_differences.mean()),
            "paired_bootstrap_95_ci": [float(lower), float(upper)],
            "direction": direction,
            "bootstrap_probability_of_improvement": improvement_probability,
        }

    return {
        "num_common_episodes": len(paired_keys),
        "num_baseline_episodes": len(baseline_map),
        "num_candidate_episodes": len(candidate_map),
        "bootstrap_samples": int(num_samples),
        "seed": int(seed),
        "metrics": metrics,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, required=True)
    parser.add_argument(
        "--baseline-path",
        type=str,
        default=None,
        help="optional Pano-only result directory for paired bootstrap",
    )
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    output_path = Path(args.path)
    rows = load_rows(output_path)
    baseline_rows = (
        load_rows(Path(args.baseline_path))
        if args.baseline_path is not None
        else None
    )
    summary = summarize_rows(rows)
    write_outputs(output_path, rows, summary)

    num_rows = len(rows)
    if num_rows == 0:
        print("No results found.")
        return

    for key, label in (("success", "Success rate"), ("oracle_success", "Oracle success rate")):
        values = metric_values(rows, key)
        total = sum(int(value) for value in values)
        print(f"{label}: {total}/{len(values)} ({format_metric(summary[key])})")
    print(f"SPL: {format_metric(summary['spl'])}")
    print(f"Distance to goal: {format_metric(summary['distance_to_goal'])}")
    print(f"Path length: {format_metric(summary['path_length'])}")
    print(f"ndtw: {format_metric(summary['ndtw'])}")

    if baseline_rows is not None:
        if args.bootstrap_samples <= 0:
            raise ValueError("--bootstrap-samples must be positive")
        comparison = paired_bootstrap_comparison(
            baseline_rows,
            rows,
            num_samples=args.bootstrap_samples,
            seed=args.seed,
        )
        comparison_path = output_path / PAIRED_COMPARISON_FILENAME
        comparison_path.write_text(
            json.dumps(comparison, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            "Paired bootstrap: "
            f"{comparison['num_common_episodes']} common episodes, "
            f"saved to {comparison_path}"
        )


if __name__ == "__main__":
    main()
