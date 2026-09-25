"""NaVILA Llama-3/SigLIP runtime using the official navigation conversation."""
from .common import BasePredictor, InferenceConfig, navila_frames, parse_metric_action
DEFAULT_MODEL_PATH = './checkpoints/NaVILA'

class Predictor(BasePredictor):
    method='NaVILA'
    action_sequence_length=64

    def load(self):
        from .runtime_paths import activate_model_code
        activate_model_code()
        from llava.model.builder import load_pretrained_model
        self.tokenizer,self.model,self.image_processor,_=load_pretrained_model(
            self.config.model_path,'navila',device_map={'':str(self.device)},device=str(self.device),
            attn_implementation=self.config.attn_implementation,vision_tower=self.config.vision_tower)
        self.model.eval()
        self.num_video_frames=int(getattr(self.model.config,'num_video_frames',8))

    def infer(self,instruction,new_images):
        import torch
        from llava.constants import IMAGE_TOKEN_INDEX
        from llava.conversation import conv_templates, SeparatorStyle
        from llava.mm_utils import process_images, tokenizer_image_token, KeywordsStoppingCriteria
        images=navila_frames(self.images,self.num_video_frames)
        image_token='<image>\n'
        qs=(f'Imagine you are a robot programmed for navigation tasks. You have been given a video '
            f'of historical observations {image_token*(len(images)-1)}, and current observation <image>\n. Your assigned task is: "{instruction}" '
            f'Analyze this series of images to decide your next action, which could be turning left or right by a specific '
            f'degree, moving forward a certain distance, or stop if the task is completed.')
        conv=conv_templates['llama_3'].copy()
        conv.append_message(conv.roles[0],qs); conv.append_message(conv.roles[1],None)
        input_ids=tokenizer_image_token(conv.get_prompt(),self.tokenizer,IMAGE_TOKEN_INDEX,return_tensors='pt').unsqueeze(0).to(self.device)
        pixels=process_images(images,self.image_processor,self.model.config).to(self.device,dtype=torch.float16)
        stop=conv.sep if conv.sep_style!=SeparatorStyle.TWO else conv.sep2
        output,elapsed=self.generate(self.model.generate,input_ids,images=pixels,do_sample=False,
            temperature=0.0,max_new_tokens=1024,use_cache=True,
            stopping_criteria=[KeywordsStoppingCriteria([stop],self.tokenizer,input_ids)],
            pad_token_id=self.tokenizer.eos_token_id)
        # Official NaVILA generate delegates via inputs_embeds: output is completion only.
        text=self.tokenizer.batch_decode(output,skip_special_tokens=True)[0].strip()
        if stop and text.endswith(stop): text=text[:-len(stop)].strip()
        return text,len(images),elapsed

    def parse(self,text):
        return parse_metric_action(text,'navila')
