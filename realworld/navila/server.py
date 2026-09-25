"""Serialized, episode-scoped HTTP server for the real robot client."""
from __future__ import annotations
import argparse
import base64
import binascii
import json
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool
from .inference import DEFAULT_MODEL_PATH, InferenceConfig, Predictor

class PredictionOptions(BaseModel):
    episode_id: str = Field(..., min_length=1)
    observation_start: int = Field(default=0, ge=0)
    include_uncertainty: bool = False
    uncertainty_max_actions: int = Field(default=8,gt=0)

class PredictJsonRequest(PredictionOptions):
    instruction: str
    images: list[str]

class ResetRequest(BaseModel):
    episode_id: str = Field(..., min_length=1)

def create_app(settings, predictor, *, log_dir=None):
    app=FastAPI(title=f'{predictor.method} real-world inference')
    lock=threading.RLock()
    state={'episode_id':None,'observations':0,'instruction':None,'failed':False}
    log_path=Path(log_dir)/'inference.jsonl' if log_dir else None
    if log_path: log_path.parent.mkdir(parents=True,exist_ok=True)

    @app.get('/health')
    @app.get('/ready')
    def ready():
        return {'ok':True,'model_loaded':True,'method':predictor.method,
                'model_path':settings.model_path,'action_sequence_length':predictor.action_sequence_length,
                'supports_action_uncertainty':False,'stateful':True,'protocol':'incremental-v1',
                'view_mode':'perspective','input_view':settings.input_view,'projection_location':'client',
                'settings':asdict(settings),'forward_distance_m':0.25,'turn_degrees':15}

    @app.post('/reset')
    def reset(payload: ResetRequest):
        with lock:
            predictor.reset()
            state.update(episode_id=payload.episode_id,observations=0,instruction=None,failed=False)
        return {'ok':True,'episode_id':payload.episode_id}

    def run_prediction(instruction, images, options, request_id, received):
        with lock:
            if options.include_uncertainty:
                raise HTTPException(400,'Use actions_per_replan=0; this baseline does not provide PanoVLN uncertainty')
            if state['episode_id'] != options.episode_id:
                raise HTTPException(409,'Unknown episode; POST /reset before starting a route')
            if state['failed']:
                raise HTTPException(409,'Previous prediction failed; reset the episode before continuing')
            if options.observation_start != state['observations']:
                raise HTTPException(409,'Observation offset mismatch; duplicate or missing frames')
            instruction=instruction.strip()
            if state['instruction'] not in (None,instruction):
                raise HTTPException(409,'Instruction changed within an episode; reset first')
            row={'request_id':request_id,'timestamp':datetime.now(timezone.utc).isoformat(),
                 'method':predictor.method,'episode_id':options.episode_id,
                 'observation_start':options.observation_start,'images':len(images),'status':'succeeded',
                 'queue_s':time.perf_counter()-received}
            start=time.perf_counter()
            try:
                result=predictor.predict(instruction=instruction,images=images)
                payload=asdict(result)
                state['observations']+=len(images)
                state['instruction']=instruction
                row.update(raw_text=result.raw_text,actions=result.actions,inference_s=result.inference_s)
            except Exception as exc:
                state['failed']=True
                row.update(status='failed',error=f'{type(exc).__name__}: {exc}')
                raise HTTPException(500,str(exc)) from exc
            finally:
                row.update(predict_s=time.perf_counter()-start,server_s=time.perf_counter()-received)
                if log_path:
                    with log_path.open('a',encoding='utf-8') as file:
                        file.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
            payload.update(request_id=request_id,server_s=row['server_s'],episode_id=options.episode_id,
                           observation_count=state['observations'])
            return payload

    async def dispatch(request,instruction,images,options):
        if not instruction.strip() or not images or any(not image for image in images):
            raise HTTPException(400,'Provide a nonempty instruction and at least one image')
        return await run_in_threadpool(run_prediction,instruction,images,options,
                                      request.headers.get('X-Request-ID') or str(uuid4()),time.perf_counter())

    @app.post('/predict')
    async def predict(request: Request):
        async with request.form() as form:
            try:
                options=PredictionOptions(**{key:form[key] for key in
                    ('episode_id','observation_start','include_uncertainty','uncertainty_max_actions') if key in form})
            except ValidationError as exc:
                raise HTTPException(422,str(exc)) from exc
            instruction=str(form.get('instruction',''))
            images=[]
            for key in ('images','image','files','file'):
                for upload in form.getlist(key):
                    if hasattr(upload,'read'): images.append(await upload.read())
        return await dispatch(request,instruction,images,options)

    @app.post('/predict_json')
    async def predict_json(payload: PredictJsonRequest,request: Request):
        try:
            images=[base64.b64decode(image,validate=True) for image in payload.images]
        except (ValueError,binascii.Error) as exc:
            raise HTTPException(400,'Invalid base64 image') from exc
        return await dispatch(request,payload.instruction,images,payload)
    return app

def parse_args():
    p=argparse.ArgumentParser(description='Serve the official baseline on the Go2 HTTP protocol')
    p.add_argument('--host',default='0.0.0.0'); p.add_argument('--port',type=int,default=8000)
    p.add_argument('--model-path',default=DEFAULT_MODEL_PATH)
    p.add_argument('--device',default='cuda:0')
    p.add_argument('--attn-implementation',default='flash_attention_2')
    p.add_argument('--input-view',choices=['perspective'],default='perspective',
                   help='Receive perspective frames projected by the robot client')
    p.add_argument('--perspective-hfov',type=float,default=InferenceConfig.perspective_hfov)
    p.add_argument('--perspective-yaw',type=float,default=0)
    p.add_argument('--perspective-pitch',type=float,default=0)
    p.add_argument('--perspective-width',type=int,default=InferenceConfig.perspective_width)
    p.add_argument('--perspective-height',type=int,default=InferenceConfig.perspective_height)
    p.add_argument('--num-history',type=int,default=8,help='JanusVLN/StreamVLN historical frame count')
    p.add_argument('--num-frames',type=int,default=32,help='StreamVLN cache reset window, in executed atoms')
    p.add_argument('--seed',type=int,default=0)
    p.add_argument('--max-episode-frames',type=int,default=4096)
    p.add_argument('--vision-tower',default=None,help='Optional vision backbone path override')
    p.add_argument('--image-processor',default=None,help='Optional visual processor path override (NaVid)')
    p.add_argument('--log-dir',default=None)
    return p.parse_args()

def main():
    args=parse_args(); values=vars(args).copy()
    host=values.pop('host'); port=values.pop('port'); log_dir=values.pop('log_dir')
    settings=InferenceConfig(**values)
    print(json.dumps(asdict(settings),ensure_ascii=False,indent=2),flush=True)
    predictor=Predictor(settings)
    uvicorn.run(create_app(settings,predictor,log_dir=log_dir),host=host,port=port)

if __name__=='__main__': main()
