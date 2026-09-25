"""Robot-facing inference contracts and observation geometry (no model imports)."""
from dataclasses import dataclass
from pathlib import Path
import io
import math
import re

@dataclass
class InferenceConfig:
    model_path: str = './checkpoints/StreamVLN'
    device: str = 'cuda:0'
    attn_implementation: str = 'flash_attention_2'
    input_view: str = 'perspective'
    perspective_hfov: float = 79.0
    perspective_yaw: float = 0.0
    perspective_pitch: float = 0.0
    perspective_width: int = 640
    perspective_height: int = 480
    num_history: int = 8
    num_frames: int = 32
    seed: int = 0
    max_episode_frames: int = 4096
    vision_tower: str | None = None
    image_processor: str | None = None

@dataclass
class PredictionResult:
    actions: list[str]
    executable_actions: list[str]
    raw_text: str
    prompt_images: int
    latency_s: float
    inference_s: float | None = None
    uncertainty_actions: list[str] | None = None
    action_uncertainties: list[float] | None = None


def load_image(value):
    from PIL import Image
    if isinstance(value, Image.Image):
        return value.convert('RGB')
    with Image.open(io.BytesIO(value) if isinstance(value, (bytes, bytearray)) else value) as image:
        return image.convert('RGB')


def prepare_view(value, config):
    """Decode the client's perspective JPEG; never project it again on the server."""
    if config.input_view != 'perspective':
        raise ValueError('ERP projection must run on the client; set input_view=perspective')
    image = load_image(value)
    expected = (config.perspective_width, config.perspective_height)
    if image.size != expected:
        raise ValueError(
            f'Expected a client-projected perspective image of {expected[0]}x{expected[1]}, '
            f'got {image.width}x{image.height}; check client camera.perspective_* settings'
        )
    return image


def executable(actions):
    if not actions:
        raise ValueError('Model returned no executable action')
    return actions[:actions.index('stop')+1] if 'stop' in actions else list(actions)


def parse_discrete(text, limit):
    pattern = r'(?<![a-z_])(?:move[_ ]forward|turn[_ ]left|turn[_ ]right|forward|left|right|stop)(?![a-z_])|[↑←→]'
    mapping = {'↑':'forward','←':'left','→':'right'}
    actions = [mapping.get(m, m.replace('_',' ').split()[-1]) for m in re.findall(pattern, text.lower())]
    return executable(actions[:limit])


def parse_metric_action(text, method):
    """Official distance quantization, mapped onto 25cm/15deg Go2 atoms.

    NaVid clips to three 25cm/30deg steps. NaVILA uses 25cm/15deg.
    Malformed outputs fail the request instead of moving randomly as in simulation.
    """
    text = text.lower().strip()
    if re.search(r'\bstop\b',text):
        return ['stop']
    match = re.search(r'\b(?:move\s+)?(forward|left|right)\s+(?:by\s+)?(-?\d+(?:\.\d+)?)\s*(cm|centimeters?|m|meters?|degrees?|deg|°)?',text)
    if not match:
        raise ValueError(f'Cannot parse {method} action: {text!r}')
    action, number, unit = match.groups()
    value = float(number)
    if value <= 0 or not math.isfinite(value):
        raise ValueError('Action magnitude must be positive')
    if action == 'forward' and unit in {'m','meter','meters'}:
        value *= 100
    if method == 'navid':
        count = min(3, int(value / (25 if action == 'forward' else 30)))
        count *= 1 if action == 'forward' else 2
    elif method == 'navila':
        quantum = 25 if action == 'forward' else 15
        if value % quantum:
            value = min(([25,50,75] if action == 'forward' else [15,30,45]),key=lambda v: abs(v-value))
        count = int(value // quantum)
    else:
        raise ValueError(method)
    if count < 1 or count > 64:
        raise ValueError('Action magnitude outside supported executable range')
    return [action]*count


def uniform_history(images, count):
    import numpy as np
    if len(images) <= count+1:
        return list(images)
    return [images[i] for i in np.linspace(0,len(images)-1,count+1,dtype=int)]


def navila_frames(images, count):
    import numpy as np
    from PIL import Image
    if count < 2:
        raise ValueError('NaVILA requires at least two video frames')
    frames = [Image.new('RGB',(512,512)) for _ in range(max(0,count-len(images)))] + list(images)
    indices = np.linspace(0,len(frames)-1,num=count-1,endpoint=False,dtype=int)
    return [frames[i] for i in indices] + [frames[-1]]


class BasePredictor:
    method = 'StreamVLN'
    action_sequence_length = 64
    def __init__(self, config):
        import torch
        import random
        import numpy as np
        if config.max_episode_frames < 1 or config.num_history < 1 or config.num_frames < 1:
            raise ValueError('Episode/history/window sizes must be positive')
        self.config = config
        random.seed(config.seed); np.random.seed(config.seed); torch.manual_seed(config.seed)
        if config.device.startswith('cuda') and not torch.cuda.is_available():
            raise RuntimeError('CUDA is unavailable; use the model server environment on a GPU machine')
        if config.image_processor and self.method != 'NaVid':
            raise ValueError('--image-processor is only supported for NaVid')
        if config.vision_tower and self.method == 'JanusVLN':
            raise ValueError('JanusVLN uses the vision towers saved in its full checkpoint')
        self.device = torch.device(config.device)
        self.images = []
        self.load()
        self.reset()

    def reset(self):
        self.images = []

    def predict(self, instruction, images, **kwargs):
        import time
        import torch
        if kwargs.get('include_uncertainty'):
            raise ValueError('PanoVLN action uncertainty is not supported by this baseline')
        if not instruction.strip() or not images:
            raise ValueError('Nonempty instruction and new images are required')
        if len(self.images)+len(images) > self.config.max_episode_frames:
            raise ValueError('Episode frame limit exceeded; finish/reset the episode')
        start = time.perf_counter()
        new_images = [prepare_view(image,self.config) for image in images]
        self.images.extend(new_images)
        with torch.inference_mode():
            text, count, inference_s = self.infer(instruction,new_images)
        actions = self.parse(text)
        return PredictionResult(actions,executable(actions),text,count,time.perf_counter()-start,inference_s)

    def generate(self, function, *args, **kwargs):
        import time
        import torch
        if self.device.type == 'cuda': torch.cuda.synchronize(self.device)
        start=time.perf_counter()
        result=function(*args,**kwargs)
        if self.device.type == 'cuda': torch.cuda.synchronize(self.device)
        return result,time.perf_counter()-start
