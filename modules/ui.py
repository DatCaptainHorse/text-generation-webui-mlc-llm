import copy
from pathlib import Path

import gradio as gr
import yaml

from modules import shared


with open(Path(__file__).resolve().parent / '../css/NotoSans/stylesheet.css', 'r') as f:
    css = f.read()
with open(Path(__file__).resolve().parent / '../css/main.css', 'r') as f:
    css += f.read()
with open(Path(__file__).resolve().parent / '../js/main.js', 'r') as f:
    js = f.read()
with open(Path(__file__).resolve().parent / '../js/save_files.js', 'r') as f:
    save_files_js = f.read()
with open(Path(__file__).resolve().parent / '../js/switch_tabs.js', 'r') as f:
    switch_tabs_js = f.read()
with open(Path(__file__).resolve().parent / '../js/show_controls.js', 'r') as f:
    show_controls_js = f.read()

refresh_symbol = '🔄'
delete_symbol = '🗑️'
save_symbol = '💾'

theme = gr.themes.Default(
    font=['Noto Sans', 'Helvetica', 'ui-sans-serif', 'system-ui', 'sans-serif'],
    font_mono=['IBM Plex Mono', 'ui-monospace', 'Consolas', 'monospace'],
).set(
    border_color_primary='#c5c5d2',
    button_large_padding='6px 12px',
    body_text_color_subdued='#484848',
    background_fill_secondary='#eaeaea'
)

if Path("notification.mp3").exists():
    audio_notification_js = "document.querySelector('#audio_notification audio')?.play();"
else:
    audio_notification_js = ""


def list_model_elements():
    elements = [
    ]

    return elements


def list_interface_input_elements():
    elements = [
        'max_new_tokens',
        'temperature',
        'top_p',
        'repetition_penalty',
        'add_bos_token',
        'stream',
    ]

    # Chat elements
    elements += [
        'textbox',
        'start_with',
        'character_menu',
        'history',
        'name1',
        'name2',
        'greeting',
        'context',
        'mode',
        'instruction_template',
        'name1_instruct',
        'name2_instruct',
        'context_instruct',
        'turn_template',
        'chat_style',
        'chat-instruct_command',
    ]

    # Notebook/default elements
    elements += [
        'textbox-notebook',
        'textbox-default',
        'output_textbox',
        'prompt_menu-default',
        'prompt_menu-notebook',
    ]

    # Model elements
    elements += list_model_elements()

    return elements


def gather_interface_values(*args):
    output = {}
    for i, element in enumerate(list_interface_input_elements()):
        output[element] = args[i]

    if not shared.args.multi_user:
        shared.persistent_interface_state = output

    return output


def apply_interface_values(state, use_persistent=False):
    if use_persistent:
        state = shared.persistent_interface_state

    elements = list_interface_input_elements()
    if len(state) == 0:
        return [gr.update() for k in elements]  # Dummy, do nothing
    else:
        return [state[k] if k in state else gr.update() for k in elements]


def save_settings(state, preset, instruction_template, extensions, show_controls):
    output = copy.deepcopy(shared.settings)
    exclude = ['name2', 'greeting', 'context', 'turn_template']
    for k in state:
        if k in shared.settings and k not in exclude:
            output[k] = state[k]

    output['preset'] = preset
    output['prompt-default'] = state['prompt_menu-default']
    output['prompt-notebook'] = state['prompt_menu-notebook']
    output['character'] = state['character_menu']
    output['instruction_template'] = instruction_template
    output['default_extensions'] = extensions
    output['seed'] = int(output['seed'])
    output['show_controls'] = show_controls

    return yaml.dump(output, sort_keys=False, width=float("inf"))


def create_refresh_button(refresh_component, refresh_method, refreshed_args, elem_class, interactive=True):
    """
    Copied from https://github.com/AUTOMATIC1111/stable-diffusion-webui
    """
    def refresh():
        refresh_method()
        args = refreshed_args() if callable(refreshed_args) else refreshed_args

        for k, v in args.items():
            setattr(refresh_component, k, v)

        return gr.update(**(args or {}))

    refresh_button = gr.Button(refresh_symbol, elem_classes=elem_class, interactive=interactive)
    refresh_button.click(
        fn=refresh,
        inputs=[],
        outputs=[refresh_component]
    )

    return refresh_button
