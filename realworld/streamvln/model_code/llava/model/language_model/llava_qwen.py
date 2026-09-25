#    Copyright 2024 Hao Zhang
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


from transformers import AutoConfig, Qwen2Config, Qwen2Model
from llava.model.llava_arch import LlavaMetaModel

class LlavaQwenConfig(Qwen2Config):
    model_type = "llava_qwen"

    def get_text_config(self, decoder=None, encoder=None):
        # StreamVLN stores its Qwen2 parameters at the top level. Some official
        # checkpoints also contain unused default LLaVA text_config metadata.
        return self

class LlavaQwenModel(LlavaMetaModel, Qwen2Model):
    config_class = LlavaQwenConfig

    def __init__(self, config: Qwen2Config):
        super(LlavaQwenModel, self).__init__(config)

AutoConfig.register("llava_qwen", LlavaQwenConfig)
