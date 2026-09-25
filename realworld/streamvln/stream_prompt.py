"""Extracted from official streamvln_agent.py:preprocess_qwen."""
import torch
import transformers
DEFAULT_IMAGE_TOKEN="<image>"
IMAGE_TOKEN_INDEX=-200
MEMORY_TOKEN_INDEX=-300
def preprocess_qwen(sources, tokenizer: transformers.PreTrainedTokenizer, has_image: bool=False, max_len=2048, system_message: str='You are a helpful assistant.', add_system: bool=False):
    roles = {'human': 'user', 'gpt': 'assistant'}
    image_token_index = tokenizer.convert_tokens_to_ids('<image>')
    memory_token_index = tokenizer.convert_tokens_to_ids('<memory>')
    im_start = tokenizer.convert_tokens_to_ids("<|im_start|>")
    im_end = tokenizer.convert_tokens_to_ids("<|im_end|>")
    unmask_tokens_idx = [198, im_start, im_end]
    nl_tokens = tokenizer('\n').input_ids
    chat_template = "{% for message in messages %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% endif %}"
    tokenizer.chat_template = chat_template
    conversations = []
    input_ids = []
    for i, source in enumerate(sources):
        prompt = 'you can see ' + DEFAULT_IMAGE_TOKEN
        if len(source[0]['value']) != 0:
            source[0]['value'] += f' {prompt}.'
        else:
            source[0]['value'] = f'{prompt}.'
        if roles[source[0]['from']] != roles['human']:
            source = source[1:]
        input_id, target = ([], [])
        if add_system:
            input_id += tokenizer.apply_chat_template([{'role': 'system', 'content': system_message}], return_dict=False)
        for conv in source:
            try:
                role = conv['role']
                content = conv['content']
            except:
                role = conv['from']
                content = conv['value']
            role = roles.get(role, role)
            conv = [{'role': role, 'content': content}]
            conversations.append(content)
            encode_id = tokenizer.apply_chat_template(conv, return_dict=False)
            input_id += encode_id
        for idx, encode_id in enumerate(input_id):
            if encode_id == image_token_index:
                input_id[idx] = IMAGE_TOKEN_INDEX
            if encode_id == memory_token_index:
                input_id[idx] = MEMORY_TOKEN_INDEX
        input_ids.append(input_id)
    input_ids = torch.tensor(input_ids, dtype=torch.long)
    return (input_ids, conversations)
