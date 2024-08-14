from transformers import (
    LlamaForCausalLM, 
    LlamaTokenizer,
    AutoModelForCausalLM,
    AutoTokenizer,
)
import torch

llm_map = {
    # "llama-2-7B": "meta-llama/Llama-2-7b",  Llama-2-7b-hf
    "llama-2-7B": "meta-llama/Llama-2-7b-chat-hf",
    
    "llama-2-70B": "meta-llama/Llama-2-70b-hf",
    # "llama-3-8B": "meta-llama/Meta-Llama-3-8B", meta-llama/Meta-Llama-3.1-8B
    "llama-3-8B": "meta-llama/Meta-Llama-3.1-8B", 
    # "llama-3-70B": "meta-llama/Meta-Llama-3-70B", meta-llama/Meta-Llama-3.1-70B
    "llama-3-70B": "meta-llama/Meta-Llama-3.1-70B",
    "mixtral-8x7B": "mistralai/Mixtral-8x7B-v0.1",
    "mixtral-8x7B-instruct": "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "phi-3-mini-128k-instruct": "microsoft/Phi-3-mini-128k-instruct",
}


DEFAULT_EOS_TOKEN = "</s>"
DEFAULT_BOS_TOKEN = "<s>"
DEFAULT_UNK_TOKEN = "<unk>"


def get_tokenizer(llm_path, llm_type, access_token):
    if llm_path is None:
        llm_path = llm_map[llm_type]
    if "llama-2" in llm_type:
        # tokenizer = LlamaTokenizer.from_pretrained(
        #     llm_path,
        #     use_fast=False,
        #     padding_side="left",
        #     token=access_token,
        #     cache_dir="/workspace/will/LLMP/hf_cache/"
        # )
        tokenizer = AutoTokenizer.from_pretrained(
            llm_path,
            # use_fast=False,
            padding_side="left",
            token=access_token,
            cache_dir="/workspace/will/LLMP/hf_cache/"
        )
    elif "llama-3" in llm_type:
        tokenizer = AutoTokenizer.from_pretrained(
            llm_path,
            padding_side="left",
            legacy=False,
            token=access_token,
            cache_dir="/workspace/will/LLMP/hf_cache/"
        )
    elif "phi-3" in llm_type:
        tokenizer = AutoTokenizer.from_pretrained(
            llm_path,
            trust_remote_code=True,
        )
    elif "mixtral" in llm_type:
        tokenizer = AutoTokenizer.from_pretrained(
            llm_path,
            token=access_token
        )       
    else:
        assert False

    special_tokens_dict = dict()
    if tokenizer.eos_token is None:
        special_tokens_dict["eos_token"] = DEFAULT_EOS_TOKEN
    if tokenizer.bos_token is None:
        special_tokens_dict["bos_token"] = DEFAULT_BOS_TOKEN
    if tokenizer.unk_token is None:
        special_tokens_dict["unk_token"] = DEFAULT_UNK_TOKEN

    tokenizer.add_special_tokens(special_tokens_dict)
    tokenizer.pad_token = tokenizer.eos_token

    return tokenizer


def get_model_and_tokenizer(llm_path, llm_type, token):
    print("Here")
    if llm_path is None:
        llm_path = llm_map[llm_type]
    tokenizer = get_tokenizer(llm_path, llm_type, token)
    if "llama-2" in llm_type:
        model = LlamaForCausalLM.from_pretrained(
            llm_path,
            device_map="auto",
            torch_dtype=torch.float16,
            token=token,
            cache_dir="/workspace/will/LLMP/hf_cache/"
        )
    elif "llama-3" in llm_type:
        model = LlamaForCausalLM.from_pretrained(
            llm_path,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            token=token,
            cache_dir="/workspace/will/LLMP/hf_cache/"
        )
    elif "phi-3" in llm_type:
        model = AutoModelForCausalLM.from_pretrained(
            llm_path,
            device_map="cuda",
            torch_dtype="auto",
            trust_remote_code=True,
        )
    elif "mixtral" in llm_type:
        model = AutoModelForCausalLM.from_pretrained(
            llm_path,
            trust_remote_code=True,
            torch_dtype=torch.float16,
            device_map='auto',
            token=token
        )
    else:
        assert False

    model.eval()
    return model, tokenizer


# This assumes that there is only a single prompt and it gets replicated batch_size times
@torch.inference_mode()
def hf_generate(
    model,
    tokenizer,
    input_str,
    batch_size,
    temp, 
    top_p,
    max_new_tokens
    ):
    batch = tokenizer([input_str], return_tensors="pt")
    batch = {k: v.repeat(batch_size, 1) for k, v in batch.items()}
    batch = {k: v.cuda() for k, v in batch.items()}
    num_input_ids = batch['input_ids'].shape[1]

    generate_ids = model.generate(
        **batch,
        do_sample=True,
        max_new_tokens=max_new_tokens,
        temperature=temp, 
        top_p=top_p, 
        renormalize_logits=False,
        pad_token_id=tokenizer.eos_token_id
    )

    gen_strs = tokenizer.batch_decode(
        generate_ids[:, num_input_ids:],
        skip_special_tokens=True, 
        clean_up_tokenization_spaces=False
    )

    return gen_strs


# this assumes a batch of different prompts that may be different lengths
@torch.inference_mode()
def hf_generate_batch(
    model,
    tokenizer,
    prompts,
    temp,
    top_p,
    max_new_tokens
    ):
    batch = tokenizer(prompts, return_tensors="pt", padding=True)
    batch = {k: v.cuda() for k, v in batch.items()}
    num_input_ids = batch['input_ids'].shape[1]

    generate_ids = model.generate(
        **batch,
        do_sample=True,
        max_new_tokens=max_new_tokens,
        temperature=temp,
        top_p=top_p,
        renormalize_logits=False,
        pad_token_id=tokenizer.eos_token_id
    )
    # print(f"generate_ids shape.: {generate_ids.shape}")
    # print(f"generate_ids[0]: {generate_ids[0, num_input_ids:]}")
    gen_strs = tokenizer.batch_decode(
        generate_ids[:, num_input_ids:],
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )
    # print(f"gen_strs[0]: {gen_strs[0]}")

    return gen_strs
