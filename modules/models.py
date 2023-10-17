import re
import time

import mlc_chat

import modules.shared as shared
from modules.logging_colors import logger

local_rank = None

mlc_model_conv_config = mlc_chat.ConvConfig(
    separator_style=0,
    seps=[" "],
    role_msg_sep=" ",
    role_empty_sep=" ",
    stop_tokens=[2],
    stop_str="</s>",
    add_bos=True,
)
mlc_model_config = mlc_chat.ChatConfig(conv_config=mlc_model_conv_config, conv_template=None)

def load_model(model_name):
    logger.info(f"Loading {model_name}...")
    t0 = time.time()

    model = mlc_llm_loader(model_name)

    logger.info(f"Loaded the model in {(time.time()-t0):.2f} seconds.")
    return model


def mlc_llm_loader(model_name):
    model = mlc_chat.ChatModule(model=f"./models/{model_name}", chat_config=mlc_model_config)
    return model


def unload_model():
    shared.model = None
    shared.lora_names = []
    shared.model_dirty_from_training = False


def reload_model():
    unload_model()
    shared.model = load_model(shared.model_name)
