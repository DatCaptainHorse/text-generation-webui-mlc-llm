from pathlib import Path

import yaml

from modules import utils


def load_prompt(fname):
    if fname in ['None', '']:
        return ''
    else:
        file_path = Path(f'prompts/{fname}.txt')
        if not file_path.exists():
            return ''

        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            if text[-1] == '\n':
                text = text[:-1]

            return text


def load_instruction_prompt_simple(fname):
    file_path = Path(f'instruction-templates/{fname}.yaml')
    if not file_path.exists():
        return ''

    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        output = ''
        if 'context' in data:
            output += data['context']

        replacements = {
            '<|user|>': data['user'],
            '<|bot|>': data['bot'],
            '<|user-message|>': 'Input',
        }

        output += utils.replace_all(data['turn_template'].split('<|bot-message|>')[0], replacements)
        return output.rstrip(' ')


def count_tokens(text):
    try:
        return text
    except:
        return '0'
