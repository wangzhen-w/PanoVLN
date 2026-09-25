#    Copyright 2023 Haotian Liu
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


from typing import List, Optional, Tuple, Union

import torch
import torch.nn as nn
from torch.nn import CrossEntropyLoss

from transformers import AutoConfig, AutoModelForCausalLM, \
                         LlamaConfig, LlamaModel, LlamaForCausalLM

from transformers.modeling_outputs import CausalLMOutputWithPast

from navid.model.navid_arch import NaVidMetaModel, NaVidMetaForCausalLM
from navid.constants import NAVIGATION_IDENTIFIER

class LlavaConfig(LlamaConfig):
    model_type = "navid"

class LlavaAttLlamaModel(NaVidMetaModel, LlamaModel):
    config_class = LlavaConfig

    def __init__(self, config: LlamaConfig):
        super(LlavaAttLlamaModel, self).__init__(config)

class LlavaLlamaAttForCausalLM(LlamaForCausalLM, NaVidMetaForCausalLM):
    config_class = LlavaConfig

    def __init__(self, config):
        super(LlamaForCausalLM, self).__init__(config)
        self.model = LlavaAttLlamaModel(config)

        self.lm_head = nn.Linear(config.hidden_size, config.vocab_size, bias=False)

        # Initialize weights and apply final processing
        self.post_init()



    def get_model(self):
        return self.model

    def forward(
        self, input_ids=None, attention_mask=None, position_ids=None,
        past_key_values=None, inputs_embeds=None, labels=None, use_cache=None,
        images=None, prompts=None, **kwargs,
    ):
        if inputs_embeds is None:
            if images is not None:
                images = [image.to(self.device) for image in images]
            input_ids, attention_mask, past_key_values, inputs_embeds, labels = (
                self.prepare_inputs_labels_for_multimodal(
                    input_ids, attention_mask, past_key_values, labels, images, prompts=prompts
                )
            )
            # Image/video expansion changes the sequence length. Llama derives
            # positions from the expanded embeddings and the current cache length.
            position_ids = None
        return super().forward(
            input_ids=input_ids, attention_mask=attention_mask, position_ids=position_ids,
            past_key_values=past_key_values, inputs_embeds=inputs_embeds,
            labels=labels, use_cache=use_cache, **kwargs,
        )

    def prepare_inputs_for_generation(self, input_ids, images=None, **kwargs):
        model_inputs = super().prepare_inputs_for_generation(input_ids, **kwargs)
        model_inputs["images"] = images
        return model_inputs


AutoConfig.register("navid", LlavaConfig)
AutoModelForCausalLM.register(LlavaConfig, LlavaLlamaAttForCausalLM)
