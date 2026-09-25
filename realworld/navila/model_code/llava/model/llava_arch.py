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

import logging
import os
import os.path as osp
import warnings
from abc import ABC
from collections import OrderedDict
from typing import List, Optional, Union

import torch
import torch.distributed as dist
from transformers import AutoConfig, GenerationConfig, PreTrainedModel
from transformers.modeling_utils import ContextManagers
from transformers.initialization import no_init_weights

from llava.constants import IGNORE_INDEX, IMAGE_TOKEN_INDEX
from llava.mm_utils import process_images
from llava.model.configuration_llava import LlavaConfig
from llava.model.language_model.builder import build_llm_and_tokenizer
from llava.model.multimodal_encoder.builder import build_vision_tower
from llava.model.multimodal_projector.builder import build_mm_projector
from llava.model.utils import get_model_config


# TODO decide whether should we use metaclass
class LlavaMetaModel(ABC):
    def init_vlm(self, config: PreTrainedModel = None, *args, **kwargs):
        # TODO(ligeng): figure out how from_config and from_pretrained works in HF implementation.
        if hasattr(self, "llm") or hasattr(self, "vision_tower") or hasattr(self, "mm_projector"):
            # already initialized, skipped
            return

        model_dtype = getattr(config, "model_dtype", "torch.float16")
        if not hasattr(config, "model_dtype"):
            warnings.warn("model_dtype not found in config, defaulting to torch.float16.")
            config.model_dtype = model_dtype

        cfgs = get_model_config(config)
        if len(cfgs) == 3:
            llm_cfg, vision_tower_cfg, mm_projector_cfg = cfgs
        else:
            raise ValueError("`llm_cfg` `mm_projector_cfg` `vision_tower_cfg` not found in the config.")

        # print("Before init in Config")
        # if hasattr(config, "deepspeed") and "mics" in config.deepspeed:
        #     print("Using MiCS_Init")
        #     import deepspeed
        #     with deepspeed.zero.MiCS_Init():
        #         self.llm, self.tokenizer = build_llm_and_tokenizer(llm_cfg, config, *args, **kwargs)
        #         self.vision_tower = build_vision_tower(vision_tower_cfg, config)
        #         self.mm_projector = build_mm_projector(mm_projector_cfg, config)
        # else:
        self.llm, self.tokenizer = build_llm_and_tokenizer(llm_cfg, config, *args, **kwargs)
        self.vision_tower = build_vision_tower(vision_tower_cfg, config)
        self.mm_projector = build_mm_projector(mm_projector_cfg, config)

        self.post_config()
        self.is_loaded = True

        assert (
            self.llm is not None or self.vision_tower is not None or self.mm_projector is not None
        ), "At least one of the components must be instantiated."

    @classmethod
    def load_from_config(cls, model_path_or_config, *args, **kwargs):
        pass

    ## FIXME we will use this function to load model in the future
    @classmethod
    def load_pretrained(cls, model_path_or_config, *args, **kwargs):
        kwargs.pop("config", None)

        if isinstance(model_path_or_config, str):
            config = AutoConfig.from_pretrained(model_path_or_config)
        elif isinstance(model_path_or_config, LlavaConfig):
            config = model_path_or_config
        else:
            raise NotImplementedError(
                f"wrong type, {type(model_path_or_config)} \
                                      {isinstance(model_path_or_config, LlavaConfig)}"
            )

        model_dtype = getattr(config, "model_dtype", "torch.float16")
        if not hasattr(config, "model_dtype"):
            warnings.warn("model_dtype not found in config, defaulting to torch.float16.")
            config.model_dtype = model_dtype

        cfgs = get_model_config(config)
        if len(cfgs) == 3:
            llm_cfg, vision_tower_cfg, mm_projector_cfg = cfgs
        else:
            raise ValueError("`llm_cfg` `mm_projector_cfg` `vision_tower_cfg` not found in the config.")

        # print(llm_cfg, vision_tower_cfg, mm_projector_cfg); input("DEBUG load_pretrained")
        init_context = [
            no_init_weights(),
        ]
        # print("Before Init Context")
        # if hasattr(config, "deepspeed") and "mics" in config.deepspeed:
        #     print("Using MiCS_Init")
        #     import deepspeed
        #     init_context.append(deepspeed.zero.MiCS_Init(config_dict_or_path=config.deepspeed))
        with ContextManagers(init_context):
            vlm = cls(config, *args, **kwargs)
        # print(llm_cfg, vision_tower_cfg, mm_projector_cfg); input("DEBUG load_pretrained finish")

        if hasattr(vlm, "llm") or hasattr(vlm, "vision_tower") or hasattr(vlm, "mm_projector"):
            if vlm.is_loaded:
                return vlm

        vlm.llm, vlm.tokenizer = build_llm_and_tokenizer(llm_cfg, config, *args, **kwargs)
        vlm.vision_tower = build_vision_tower(vision_tower_cfg, config)
        vlm.mm_projector = build_mm_projector(mm_projector_cfg, config)

        self.post_config()
        self.is_loaded = True

        # FIXME(ligeng, yunhao): llm should never be none here.
        assert (
            vlm.llm is not None or vlm.vision_tower is not None or vlm.mm_projector is not None
        ), "At least one of the components must be instantiated."
        return vlm

    ## FIXME we will use this function to save the model in the future

    def get_llm(self):
        llm = getattr(self, "llm", None)
        if type(llm) is list:
            llm = llm[0]
        return llm

    def get_lm_head(self):
        lm_head = getattr(self.get_llm(), "lm_head", None)
        return lm_head

    def get_vision_tower(self):
        vision_tower = getattr(self, "vision_tower", None)
        if type(vision_tower) is list:
            vision_tower = vision_tower[0]
        return vision_tower

    def get_mm_projector(self):
        mm_projector = getattr(self, "mm_projector", None)
        if type(mm_projector) is list:
            mm_projector = mm_projector[0]
        return mm_projector

    def post_config(self):
        self.training = self.get_llm().training
        ## configuration
        if getattr(self.config, "llm_cfg", None) is None:
            self.config.llm_cfg = self.llm.config
        if getattr(self.config, "vision_tower_cfg", None) is None:
            self.config.vision_tower_cfg = self.vision_tower.config
        if getattr(self.config, "mm_projector_cfg", None) is None:
            self.config.mm_projector_cfg = self.mm_projector.config

    def freezed_module_patch(self):
        """
        Huggingface will call model.train() at each training_step. To ensure the expected behaviors for modules like dropout, batchnorm, etc., we need to call model.eval() for the freezed modules.
        """
        if self.training:
            if self.get_llm() and not getattr(self.config, "tune_language_model", False):
                pass
                # logging.warning("Caution: Your LLM is currently in training mode, ensuring accurate gradient computation. Please be vigilant, particularly regarding BatchNorm and Dropout operations.")
            if self.get_vision_tower() and not getattr(self.config, "tune_vision_tower", False):
                self.get_vision_tower().eval()
            if self.get_mm_projector() and not getattr(self.config, "tune_mm_projector", False):
                self.get_mm_projector().eval()

    def encode_images(self, images):
        image_features = self.get_vision_tower()(images)
        image_features = self.get_mm_projector()(image_features)
        return image_features

    ## @yunhao: is there a better way to handle function call and attributes for llm?
    ## support beam search
    def _temporary_reorder_cache(self, past_key_values, sorted_idx):
        return self.get_llm()._temporary_reorder_cache(past_key_values, sorted_idx)

    def get_input_embeddings(self):
        return self.get_llm().get_input_embeddings()

    def get_output_embeddings(self):
        return self.get_llm().get_output_embeddings()

    def resize_token_embeddings(self, embed_size):
        self.get_llm().resize_token_embeddings(embed_size)


class LlavaMetaForCausalLM(ABC):
    """This class is originally implemented by the LLaVA team and
    modified by Haotian Tang and Jason Lu based on Ji Lin's implementation
    to support multiple images and input packing."""

    ## TODO move the forward function here if there is no need to override it
    def prepare_inputs_labels_for_multimodal(
        self, input_ids, position_ids, attention_mask, past_key_values, labels, images
    ):

        # Handle sequence parallelism
        PROCESS_GROUP_MANAGER = None
        if PROCESS_GROUP_MANAGER is None:
            sp_degree = -1
            sp_rank = -1
        else:
            sp_degree = PROCESS_GROUP_MANAGER.sp_degree
            sp_rank = PROCESS_GROUP_MANAGER.sp_rank

        vision_tower = self.get_vision_tower()
        if vision_tower is None or images is None or (input_ids.shape[1] == 1 and PROCESS_GROUP_MANAGER is None):
            if (
                past_key_values is not None
                and vision_tower is not None
                and images is not None
                and input_ids.shape[1] == 1
            ):
                target_shape = past_key_values.get_seq_length() + 1
                attention_mask = torch.cat(
                    (
                        attention_mask,
                        torch.ones(
                            (
                                attention_mask.shape[0],
                                target_shape - attention_mask.shape[1],
                            ),
                            dtype=attention_mask.dtype,
                            device=attention_mask.device,
                        ),
                    ),
                    dim=1,
                )
                position_ids = torch.sum(attention_mask, dim=1).unsqueeze(-1) - 1
            return (
                input_ids,
                position_ids,
                attention_mask,
                past_key_values,
                None,
                labels,
            )
        # handle different image dtypes for packing
        if type(images) is list:
            images = torch.cat(images, dim=0)
        elif images.ndim == 5:  # batch_size x seq_len x image_channels
            images = images.flatten(0, 1)
        image_features = self.encode_images(images).to(self.device)
        # Note (kentang-mit@): image start / end is not implemented here to support pretraining.
        if getattr(self.config, "turn_mm_projector", False) and getattr(self.config, "mm_use_im_start_end", False):
            raise NotImplementedError

        # Let's just add dummy tensors if they do not exist,
        # it is a headache to deal with None all the time.
        # But it is not ideal, and if you have a better idea,
        # please open an issue / submit a PR, thanks.
        _labels = labels
        _position_ids = position_ids
        _attention_mask = attention_mask
        if attention_mask is None:
            attention_mask = torch.ones_like(input_ids, dtype=torch.bool)
        else:
            attention_mask = attention_mask.bool()
        if position_ids is None:
            position_ids = torch.arange(0, input_ids.shape[1], dtype=torch.long, device=input_ids.device)
        if labels is None:
            labels = torch.full_like(input_ids, IGNORE_INDEX)

        # remove the padding using attention_mask
        input_ids_copy = input_ids.clone()
        # kentang-mit@: Otherwise tokenizer out of bounds. Embeddings of image tokens will not be used.
        input_ids_copy[input_ids_copy == IMAGE_TOKEN_INDEX] = 0
        input_embeds = self.llm.model.embed_tokens(input_ids_copy)

        input_ids = [
            cur_input_ids[cur_attention_mask] for cur_input_ids, cur_attention_mask in zip(input_ids, attention_mask)
        ]
        input_embeds_1 = [
            cur_input_embeds[cur_attention_mask]
            for cur_input_embeds, cur_attention_mask in zip(input_embeds, attention_mask)
        ]
        labels = [cur_labels[cur_attention_mask] for cur_labels, cur_attention_mask in zip(labels, attention_mask)]

        new_input_embeds = []
        new_labels = []
        cur_image_idx = 0

        # kentang-mit@: If some part of the model is executed in the loop, the the loop length needs to be a constant.
        for batch_idx, cur_input_ids in enumerate(input_ids):
            cur_input_ids = input_ids[batch_idx]
            num_images = (cur_input_ids == IMAGE_TOKEN_INDEX).sum()
            if num_images == 0:
                cur_image_features = image_features[0]
                cur_input_embeds_1 = input_embeds_1[batch_idx]
                cur_input_embeds = torch.cat([cur_input_embeds_1, cur_image_features[0:0]], dim=0)
                new_input_embeds.append(cur_input_embeds)
                new_labels.append(labels[batch_idx])
                # kenang-mit@: we do not have placeholdr image for text-only data now.
                continue

            cur_input_embeds = input_embeds_1[batch_idx]
            image_token_indices = (
                [-1] + torch.where(cur_input_ids == IMAGE_TOKEN_INDEX)[0].tolist() + [cur_input_ids.shape[0]]
            )
            cur_input_ids_noim = []
            cur_labels = labels[batch_idx]
            cur_labels_noim = []
            cur_input_embeds_no_im = []
            for i in range(len(image_token_indices) - 1):
                if sp_degree > 1 and i == 0 and sp_rank != 0:  # Handle sequence parallelism
                    cur_input_ids_noim.append(cur_input_ids[0:0])
                    cur_labels_noim.append(cur_labels[0:0])
                    cur_input_embeds_no_im.append(cur_input_embeds[0:0])
                    continue
                cur_input_ids_noim.append(cur_input_ids[image_token_indices[i] + 1 : image_token_indices[i + 1]])
                cur_labels_noim.append(cur_labels[image_token_indices[i] + 1 : image_token_indices[i + 1]])
                cur_input_embeds_no_im.append(cur_input_embeds[image_token_indices[i] + 1 : image_token_indices[i + 1]])

            cur_new_input_embeds = []
            cur_new_labels = []
            for i in range(num_images + 1):
                cur_new_input_embeds.append(cur_input_embeds_no_im[i])
                cur_new_labels.append(cur_labels_noim[i])
                if i < num_images:
                    cur_image_features = image_features[cur_image_idx]
                    cur_image_idx += 1
                    cur_new_input_embeds.append(cur_image_features)
                    cur_new_labels.append(
                        torch.full(
                            (cur_image_features.shape[0],),
                            IGNORE_INDEX,
                            device=cur_labels.device,
                            dtype=cur_labels.dtype,
                        )
                    )

            cur_new_input_embeds = torch.cat(cur_new_input_embeds)
            cur_new_labels = torch.cat(cur_new_labels)

            new_input_embeds.append(cur_new_input_embeds)
            new_labels.append(cur_new_labels)

        # Truncate sequences to max length as image embeddings can make the sequence longer
        tokenizer_model_max_length = getattr(self.llm.config, "tokenizer_model_max_length", None)
        if tokenizer_model_max_length is not None:
            if any(len(x) > tokenizer_model_max_length for x in new_input_embeds):
                warnings.warn("Inputs truncated!")
            new_input_embeds = [x[:tokenizer_model_max_length] for x in new_input_embeds]
            new_labels = [x[:tokenizer_model_max_length] for x in new_labels]
        # Combine them
        max_len = max(x.shape[0] for x in new_input_embeds)
        # max_len = tokenizer_model_max_length
        # print("Warning: using max_len as tokenizer_model_max_length")
        batch_size = len(new_input_embeds)

        new_input_embeds_padded = []
        new_labels_padded = torch.full(
            (batch_size, max_len),
            IGNORE_INDEX,
            dtype=new_labels[0].dtype,
            device=new_labels[0].device,
        )
        attention_mask = torch.zeros(
            (batch_size, max_len),
            dtype=attention_mask.dtype,
            device=attention_mask.device,
        )
        position_ids = torch.zeros((batch_size, max_len), dtype=position_ids.dtype, device=position_ids.device)

        for i, (cur_new_embed, cur_new_labels) in enumerate(zip(new_input_embeds, new_labels)):
            cur_len = cur_new_embed.shape[0]
            if getattr(self.llm.config, "tokenizer_padding_side", "right") == "left":
                new_input_embeds_padded.append(
                    torch.cat(
                        (
                            torch.zeros(
                                (max_len - cur_len, cur_new_embed.shape[1]),
                                dtype=cur_new_embed.dtype,
                                device=cur_new_embed.device,
                            ),
                            cur_new_embed,
                        ),
                        dim=0,
                    )
                )
                if cur_len > 0:
                    new_labels_padded[i, -cur_len:] = cur_new_labels
                    attention_mask[i, -cur_len:] = True
                    position_ids[i, -cur_len:] = torch.arange(
                        0, cur_len, dtype=position_ids.dtype, device=position_ids.device
                    )
            else:
                new_input_embeds_padded.append(
                    torch.cat(
                        (
                            cur_new_embed,
                            torch.zeros(
                                (max_len - cur_len, cur_new_embed.shape[1]),
                                dtype=cur_new_embed.dtype,
                                device=cur_new_embed.device,
                            ),
                        ),
                        dim=0,
                    )
                )
                if cur_len > 0:
                    new_labels_padded[i, :cur_len] = cur_new_labels
                    attention_mask[i, :cur_len] = True
                    position_ids[i, :cur_len] = torch.arange(
                        0, cur_len, dtype=position_ids.dtype, device=position_ids.device
                    )

        new_input_embeds = torch.stack(new_input_embeds_padded, dim=0)

        # if sp_degree > 1:  # Handle sequence parallelism
        #     if sp_rank not in self.global_seq_len:
        #         self.global_seq_len[sp_rank] = position_ids.shape[-1]
        #     else:
        #         assert self.global_seq_len[sp_rank] == position_ids.shape[-1]

        if _labels is None:
            new_labels = None
        else:
            new_labels = new_labels_padded

        if _attention_mask is None:
            attention_mask = None
        else:
            attention_mask = attention_mask.to(dtype=_attention_mask.dtype)

        if _position_ids is None:
            position_ids = None

        # We will not use packing here when sequence parallelism is enabled.
        if PROCESS_GROUP_MANAGER is not None:
            return (
                None,
                _position_ids,
                attention_mask,
                past_key_values,
                new_input_embeds,
                new_labels,
            )

        return (
            None,
            position_ids,
            attention_mask,
            past_key_values,
            new_input_embeds,
            new_labels,
        )


    @torch.inference_mode()
    def generate(
        self,
        input_ids: Optional[torch.FloatTensor] = None,
        images: Optional[torch.FloatTensor] = None,
        attention_mask: Optional[torch.LongTensor] = None,
        **generation_kwargs,
    ):
        if images is not None:
            (_, _, attention_mask, _, inputs_embeds, _) = self.prepare_inputs_labels_for_multimodal(
                input_ids, None, attention_mask, None, None, images
            )
        else:
            inputs_embeds = self.get_input_embeddings()(input_ids)
        inputs_embeds = inputs_embeds.to(self.dtype)

        outputs = self.llm.generate(inputs_embeds=inputs_embeds, attention_mask=attention_mask, **generation_kwargs)
        return outputs
