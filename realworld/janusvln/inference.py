"""JanusVLN inference extracted from official src/evaluation.py."""
from .common import BasePredictor, InferenceConfig, parse_discrete, uniform_history
DEFAULT_MODEL_PATH = './checkpoints/JanusVLN'

class Predictor(BasePredictor):
    method = 'JanusVLN'
    action_sequence_length = 1

    def load(self):
        from .runtime_paths import activate_model_code
        activate_model_code()
        import torch
        from transformers import AutoTokenizer, AutoProcessor
        from qwen_vl.model.configuration_qwen2_5_vl import Qwen2_5_VLConfig
        from qwen_vl.model.modeling_qwen2_5_vl import Qwen2_5_VLForConditionalGenerationForJanusVLN
        self.model = Qwen2_5_VLForConditionalGenerationForJanusVLN.from_pretrained(
            self.config.model_path,config=Qwen2_5_VLConfig.from_pretrained(self.config.model_path),
            dtype=torch.bfloat16,device_map={'':str(self.device)},
            attn_implementation=self.config.attn_implementation,mode='evaluation').eval()
        self.tokenizer=AutoTokenizer.from_pretrained(self.config.model_path,padding_side='left')
        self.processor=AutoProcessor.from_pretrained(self.config.model_path,max_pixels=1605632,
                                                     min_pixels=28*28,padding_side='left')

    def reset(self):
        super().reset()
        self.model.past_key_values_vggt=None
        self.model.rope_deltas=None

    def infer(self,instruction,new_images):
        import torch
        from qwen_vl.model.vggt.utils.load_fn import load_and_preprocess_images
        if len(new_images)!=1:
            raise ValueError('JanusVLN requires one observation/prediction per executed atom')
        images=uniform_history(self.images,self.config.num_history)
        system='You are a visual language navigation model, and your should go to the locations to complete the given task. Compare the observation and instruction to infer your current progress, and then select the correct direction from the candidates to go to the target location and finish the task.'
        context=f'These images are your historical observations and your current observation.\n Your task is to {instruction} \n You should take one of the following actions:\n MOVE_FORWARD\n TURN_LEFT\n TURN_RIGHT\n STOP.'
        message=[{'role':'system','content':system},{'role':'user','content':
                 [{'type':'image','image':im} for im in images]+[{'type':'text','text':context}]}]
        text=self.processor.apply_chat_template([message],tokenize=False,add_generation_prompt=True)
        patch=self.processor.image_processor.patch_size
        merge=self.processor.image_processor.merge_size
        image_inputs=[]
        for image in images:
            tensor=load_and_preprocess_images([image])[0]
            _,h,w=tensor.shape
            h-=(h//patch)%merge*patch; w-=(w//patch)%merge*patch
            image_inputs.append(tensor[:,:h,:w])
        inputs=self.processor(text=text,images=image_inputs,videos=None,padding=True,
                              return_tensors='pt',do_rescale=False,
                              return_mm_token_type_ids=False).to(self.device)
        # Only the current frame enters the persistent geometry cache.
        inputs['images_vggt']=[tensor.unsqueeze(0).to(self.device)]
        output,elapsed=self.generate(self.model.generate,**inputs,
            eos_token_id=self.tokenizer.eos_token_id,pad_token_id=self.tokenizer.pad_token_id,
            do_sample=False,num_beams=1,max_new_tokens=24)
        output=[row[len(prompt):] for prompt,row in zip(inputs.input_ids,output)]
        text=self.processor.batch_decode(output,skip_special_tokens=True,clean_up_tokenization_spaces=False)[0]
        return text,len(images),elapsed

    def parse(self,text):
        return parse_discrete(text,1)
