import os
import warnings

from modules.block_requests import OpenMonkeyPatch, RequestBlocker
from modules.logging_colors import logger

os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
os.environ['BITSANDBYTES_NOWELCOME'] = '1'
warnings.filterwarnings('ignore', category=UserWarning, message='TypedStorage is deprecated')
warnings.filterwarnings('ignore', category=UserWarning, message='Using the update method is deprecated')

with RequestBlocker():
    import gradio as gr

import json
import sys
import time
from functools import partial
from pathlib import Path
from threading import Lock

import yaml

from modules import (
    chat,
    shared,
    ui,
    ui_chat,
    ui_default,
    ui_file_saving,
    ui_notebook,
    ui_parameters,
    ui_session,
    utils
)
from modules.models import load_model
from modules.models_settings import (
    get_fallback_settings,
    get_model_metadata,
    update_model_parameters
)
from modules.utils import gradio


def create_interface():

    title = 'Text generation web UI'

    # Password authentication
    auth = []
    if shared.args.gradio_auth:
        auth.extend(x.strip() for x in shared.args.gradio_auth.strip('"').replace('\n', '').split(',') if x.strip())
    if shared.args.gradio_auth_path:
        with open(shared.args.gradio_auth_path, 'r', encoding="utf8") as file:
            auth.extend(x.strip() for line in file for x in line.split(',') if x.strip())
    auth = [tuple(cred.split(':')) for cred in auth]

    # Force some events to be triggered on page load
    shared.persistent_interface_state.update({
        'mode': shared.settings['mode'],
        'character_menu': shared.args.character or shared.settings['character'],
        'instruction_template': shared.settings['instruction_template'],
        'prompt_menu-default': shared.settings['prompt-default'],
        'prompt_menu-notebook': shared.settings['prompt-notebook'],
    })

    if Path("cache/pfp_character.png").exists():
        Path("cache/pfp_character.png").unlink()

    # css/js strings
    css = ui.css
    js = ui.js

    # Interface state elements
    shared.input_elements = ui.list_interface_input_elements()

    with gr.Blocks(css=css, analytics_enabled=False, title=title, theme=ui.theme) as shared.gradio['interface']:

        # Interface state
        shared.gradio['interface_state'] = gr.State({k: None for k in shared.input_elements})

        # Audio notification
        if Path("notification.mp3").exists():
            shared.gradio['audio_notification'] = gr.Audio(interactive=False, value="notification.mp3", elem_id="audio_notification", visible=False)

        # Floating menus for saving/deleting files
        ui_file_saving.create_ui()

        # Temporary clipboard for saving files
        shared.gradio['temporary_text'] = gr.Textbox(visible=False)

        # Text Generation tab
        ui_chat.create_ui()
        ui_default.create_ui()
        ui_notebook.create_ui()

        ui_parameters.create_ui(shared.settings['preset'])  # Parameters tab
        ui_session.create_ui()  # Session tab

        # Generation events
        ui_chat.create_event_handlers()
        ui_default.create_event_handlers()
        ui_notebook.create_event_handlers()

        # Other events
        ui_file_saving.create_event_handlers()
        ui_parameters.create_event_handlers()

        # Interface launch events
        if shared.settings['dark_theme']:
            shared.gradio['interface'].load(lambda: None, None, None, _js="() => document.getElementsByTagName('body')[0].classList.add('dark')")

        shared.gradio['interface'].load(lambda: None, None, None, _js=f"() => {{{js}}}")
        shared.gradio['interface'].load(None, gradio('show_controls'), None, _js=f'(x) => {{{ui.show_controls_js}; toggle_controls(x)}}')
        shared.gradio['interface'].load(partial(ui.apply_interface_values, {}, use_persistent=True), None, gradio(ui.list_interface_input_elements()), show_progress=False)
        shared.gradio['interface'].load(chat.redraw_html, gradio(ui_chat.reload_arr), gradio('display'))


    # Launch the interface
    shared.gradio['interface'].queue(concurrency_count=64)
    with OpenMonkeyPatch():
        shared.gradio['interface'].launch(
            prevent_thread_lock=True,
            share=shared.args.share,
            server_name=None if not shared.args.listen else (shared.args.listen_host or '0.0.0.0'),
            server_port=shared.args.listen_port,
            inbrowser=shared.args.auto_launch,
            auth=auth or None,
            ssl_verify=False if (shared.args.ssl_keyfile or shared.args.ssl_certfile) else True,
            ssl_keyfile=shared.args.ssl_keyfile,
            ssl_certfile=shared.args.ssl_certfile
        )

if __name__ == "__main__":

    # Load custom settings
    settings_file = None
    if shared.args.settings is not None and Path(shared.args.settings).exists():
        settings_file = Path(shared.args.settings)
    elif Path('settings.yaml').exists():
        settings_file = Path('settings.yaml')
    elif Path('settings.json').exists():
        settings_file = Path('settings.json')

    if settings_file is not None:
        logger.info(f"Loading settings from {settings_file}...")
        file_contents = open(settings_file, 'r', encoding='utf-8').read()
        new_settings = json.loads(file_contents) if settings_file.suffix == "json" else yaml.safe_load(file_contents)
        shared.settings.update(new_settings)

    # Fallback settings for models
    shared.model_config['.*'] = get_fallback_settings()
    shared.model_config.move_to_end('.*', last=False)  # Move to the beginning

    available_models = utils.get_available_models()

    # Require --model or --model-menu to be set
    if shared.args.model is None and shared.args.model_menu is False:
        logger.error('Please specify a model with --model or --model-menu')
        sys.exit(0)

    # Model defined through --model
    if shared.args.model is not None:
        shared.model_name = shared.args.model

    # Select the model from a command-line menu
    elif shared.args.model_menu:
        if len(available_models) == 0:
            logger.error('No models are available! Please download at least one.')
            sys.exit(0)
        else:
            print('The following models are available:\n')
            for i, model in enumerate(available_models):
                print(f'{i+1}. {model}')

            print(f'\nWhich one do you want to load? 1-{len(available_models)}\n')
            i = int(input()) - 1
            print()

        shared.model_name = available_models[i]

    # If any model has been selected, load it
    if shared.model_name != 'None':
        p = Path(shared.model_name)
        if p.exists():
            model_name = p.parts[-1]
            shared.model_name = model_name
        else:
            model_name = shared.model_name

        model_settings = get_model_metadata(model_name)
        shared.settings.update({k: v for k, v in model_settings.items() if k in shared.settings})  # hijacking the interface defaults
        update_model_parameters(model_settings, initial=True)  # hijacking the command-line arguments

        # Load the model
        shared.model = load_model(model_name)

    shared.generation_lock = Lock()

    # Launch the web UI
    create_interface()
    while True:
        time.sleep(0.5)
        if shared.need_restart:
            shared.need_restart = False
            time.sleep(0.5)
            shared.gradio['interface'].close()
            time.sleep(0.5)
            create_interface()
