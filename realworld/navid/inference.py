"""NaVid (not UniNaVid): official video tokens, history compression and Vicuna prompt."""
from .common import BasePredictor, InferenceConfig, parse_metric_action
DEFAULT_MODEL_PATH = './checkpoints/NaVid'

class Predictor(BasePredictor):
    method='NaVid'
    action_sequence_length=6

    def load(self):
        from .runtime_paths import activate_model_code
        activate_model_code()
        from navid.model.builder import load_pretrained_model
        self.tokenizer,self.model,self.image_processor,_=load_pretrained_model(
            self.config.model_path,None,'navid',device_map={'':str(self.device)},device=str(self.device),
            vision_tower=self.config.vision_tower,image_processor=self.config.image_processor)
        self.model.eval()

    def reset(self):
        super().reset()
        self.history_tensor=None
        self.last_actions=[]
        self.native_frames=0

    def infer(self,instruction,new_images):
        import numpy as np
        import torch
        from navid.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN, DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN
        from navid.conversation import conv_templates, SeparatorStyle
        from navid.mm_utils import tokenizer_image_token, KeywordsStoppingCriteria
        # The physical controller splits each native 30-degree turn into two
        # 15-degree atoms; only native action endpoints enter NaVid's video memory.
        if self.last_actions:
            if len(new_images)!=len(self.last_actions):
                raise ValueError('NaVid observation count differs from the executed native action queue')
            new_images=[im for i,im in enumerate(new_images)
                        if self.last_actions[i]=='forward' or (i+1)%2==0]
        video=self.image_processor.preprocess(np.asarray(new_images),return_tensors='pt')['pixel_values'].to(self.device,dtype=torch.float16)
        self.history_tensor=video if self.history_tensor is None else torch.cat((self.history_tensor,video),dim=0)
        self.native_frames+=len(new_images)
        prompt="Imagine you are a robot programmed for navigation tasks. You have been given a video of historical observations and an image of the current observation <image>. Your assigned task is: '{}'. Analyze this series of images to decide your next move, which could involve turning left or right by a specific degree or moving forward a certain distance.".format(instruction)
        question=prompt.replace(DEFAULT_IMAGE_TOKEN,'').replace('\n','')
        image_token=DEFAULT_IMAGE_TOKEN
        if self.model.config.mm_use_im_start_end:
            image_token=DEFAULT_IM_START_TOKEN+image_token+DEFAULT_IM_END_TOKEN
        conv=conv_templates['vicuna_v1'].copy()
        conv.append_message(conv.roles[0],image_token+'\n'+prompt.replace('<image>',''))
        conv.append_message(conv.roles[1],None)
        token_prompt=tokenizer_image_token(conv.get_prompt(),self.tokenizer,IMAGE_TOKEN_INDEX,return_tensors='pt').to(self.device)
        def special(text):
            return self.tokenizer(text,return_tensors='pt').input_ids[0][1:].to(self.device)
        parts=[]
        for token in token_prompt:
            if token.item()==IMAGE_TOKEN_INDEX:
                parts.extend([special('<video_special>'),special('<image_sep>'),token.reshape(1),
                              special('</video_special>'),special('<image_special>'),
                              special('</image_special>'),special('[Navigation]')])
            else: parts.append(token.reshape(1))
        input_ids=torch.cat(parts).unsqueeze(0)
        stop=conv.sep if conv.sep_style!=SeparatorStyle.TWO else conv.sep2
        criteria=KeywordsStoppingCriteria([stop],self.tokenizer,input_ids)
        self.model.update_prompt([[question]])
        output,elapsed=self.generate(self.model.generate,input_ids,images=[self.history_tensor],
            do_sample=True,temperature=0.2,max_new_tokens=1024,use_cache=True,stopping_criteria=[criteria])
        text=self.tokenizer.batch_decode(output[:,input_ids.shape[1]:],skip_special_tokens=True)[0].strip()
        if stop and text.endswith(stop): text=text[:-len(stop)].strip()
        return text,self.native_frames,elapsed

    def parse(self,text):
        self.last_actions=parse_metric_action(text,'navid')
        return self.last_actions
