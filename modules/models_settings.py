import json
import re
from pathlib import Path

import yaml

from modules import loaders, shared, ui


def get_fallback_settings():
    return {
        'n_ctx': 2048,
        'custom_stopping_strings': shared.settings['custom_stopping_strings'],
    }


def get_model_metadata(model):
    model_settings = {}

    # Get settings from models/config.yaml and models/config-user.yaml
    settings = shared.model_config
    for pat in settings:
        if re.match(pat.lower(), model.lower()):
            for k in settings[pat]:
                model_settings[k] = settings[pat][k]

    if 'loader' not in model_settings:
        loader = infer_loader(model, model_settings)
        model_settings['loader'] = loader

    # Apply user settings from models/config-user.yaml
    settings = shared.user_config
    for pat in settings:
        if re.match(pat.lower(), model.lower()):
            for k in settings[pat]:
                model_settings[k] = settings[pat][k]

    return model_settings


def infer_loader(model_name, model_settings):
    path_to_model = Path(f'{shared.args.model_dir}/{model_name}')
    if not path_to_model.exists():
        loader = None
    elif (path_to_model / 'quantize_config.json').exists() or ('wbits' in model_settings and type(model_settings['wbits']) is int and model_settings['wbits'] > 0):
        loader = 'AutoGPTQ'
    elif (path_to_model / 'quant_config.json').exists() or re.match(r'.*-awq', model_name.lower()):
        loader = 'AutoAWQ'
    elif len(list(path_to_model.glob('*.gguf'))) > 0:
        loader = 'llama.cpp'
    elif re.match(r'.*\.gguf', model_name.lower()):
        loader = 'llama.cpp'
    elif re.match(r'.*rwkv.*\.pth', model_name.lower()):
        loader = 'RWKV'
    elif re.match(r'.*exl2', model_name.lower()):
        loader = 'ExLlamav2_HF'
    else:
        loader = 'Transformers'

    return loader


# UI: update the command-line arguments based on the interface values
def update_model_parameters(state, initial=False):
    elements = ui.list_model_elements()  # the names of the parameters

    for i, element in enumerate(elements):
        if element not in state:
            continue

        value = state[element]

        if initial and element in shared.provided_arguments:
            continue

        setattr(shared.args, element, value)

# UI: update the state variable with the model settings
def apply_model_settings_to_state(model, state):
    model_settings = get_model_metadata(model)
    if 'loader' in model_settings:
        loader = model_settings.pop('loader')

        # If the user is using an alternative loader for the same model type, let them keep using it
        if not (loader == 'AutoGPTQ' and state['loader'] in ['GPTQ-for-LLaMa', 'ExLlama', 'ExLlama_HF', 'ExLlamav2', 'ExLlamav2_HF']) and not (loader == 'llama.cpp' and state['loader'] in ['llamacpp_HF', 'ctransformers']):
            state['loader'] = loader

    for k in model_settings:
        if k in state:
            if k in ['wbits', 'groupsize']:
                state[k] = str(model_settings[k])
            else:
                state[k] = model_settings[k]

    return state


# Save the settings for this model to models/config-user.yaml
def save_model_settings(model, state):
    if model == 'None':
        yield ("Not saving the settings because no model is loaded.")
        return

    with Path(f'{shared.args.model_dir}/config-user.yaml') as p:
        if p.exists():
            user_config = yaml.safe_load(open(p, 'r').read())
        else:
            user_config = {}

        model_regex = model + '$'  # For exact matches
        if model_regex not in user_config:
            user_config[model_regex] = {}

        for k in ui.list_model_elements():
            if k == 'loader' or k in loaders.loaders_and_params[state['loader']]:
                user_config[model_regex][k] = state[k]

        shared.user_config = user_config

        output = yaml.dump(user_config, sort_keys=False)
        with open(p, 'w') as f:
            f.write(output)

        yield (f"Settings for {model} saved to {p}")
