"""Fixed model contract shared by training, simulation, and the robot client."""

VLN_ACTION_SEQUENCE_LENGTH = 18


def configure_vln_model(config) -> None:
    """Validate saved model metadata before assigning the release architecture."""
    fields = {
        "action_sequence_length": VLN_ACTION_SEQUENCE_LENGTH,
        "view_mode": "panorama",
        "panovggt_feature_source": "aggregator",
        "panovggt_injection_stage": "post_merger",
        "panovggt_sampling_mode": "grouping",
    }
    for name, expected in fields.items():
        actual = getattr(config, name, expected)
        if actual != expected:
            raise ValueError(
                f"Unsupported checkpoint: {name}={actual!r}; "
                f"the released PanoVLN model requires {expected!r}."
            )
    for name, value in fields.items():
        setattr(config, name, value)
    # Old panoramic checkpoints can contain unused perspective settings.
    for name in ("perspective_xfov_degrees", "perspective_yfov_degrees",
                 "perspective_image_width", "perspective_image_height"):
        if hasattr(config, name):
            delattr(config, name)
