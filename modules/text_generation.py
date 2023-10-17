import copy
import html
import re
import time
import traceback

import modules.shared as shared
from modules.html_generator import generate_basic_html
from modules.models import mlc_model_config


def generate_reply(*args, **kwargs):
    shared.generation_lock.acquire()
    try:
        for result in _generate_reply(*args, **kwargs):
            # HACK: Remove "N. " numbers from result, in 1-9 range
            if re.match(r'^[1-9]\. ', result):
                result = re.sub(r'^[1-9]\. ', '', result)
                # Trim spaces
                result = result.strip()

            yield result
    finally:
        shared.generation_lock.release()


def _generate_reply(question, state, stopping_strings=None, is_chat=False, escape_html=False):
    # Prepare the input
    original_question = question

    mlc_model_config.repetition_penalty = state['repetition_penalty']
    mlc_model_config.temperature = state['temperature']
    mlc_model_config.top_p = state['top_p']
    mlc_model_config.max_gen_length = shared.settings['max_new_tokens']
    mlc_model_config.mean_gen_length = int(shared.settings['max_new_tokens']) // 2

    # Find the stopping strings
    all_stop_strings = []
    for st in (stopping_strings, shared.settings["custom_stopping_strings"]):
        if type(st) is list and len(st) > 0:
            all_stop_strings += st

    if shared.args.verbose:
        print(f'\n\n{question}\n--------------------\n')

    shared.stop_everything = False
    reply = ''
    if len(all_stop_strings) > 0 and not state['stream']:
        state = copy.deepcopy(state)
        state['stream'] = True

    # Generate
    for resp in generate_reply_mlc(question, original_question, state, stopping_strings, is_chat=is_chat):
        # Add to reply
        reply = resp

        if escape_html:
            reply = html.escape(reply)

        stop_found = False

        # HACK: If "[INST]" in reply, cut past
        if "[INST]" in reply:
            insts = reply.split("[INST]")
            # Get the response with bot name + ':' in it
            for inst in insts:
                if state['name2'] + ':' in inst:
                    reply = inst
                    break

            # Trim spaces
            reply = reply.strip()

        # HACK: If "[/INST]" in reply, replace with nothing
        if "[/INST]" in reply:
            reply = reply.replace("[/INST]", "")
            # Trim spaces
            reply = reply.strip()

        # HACK: state['name2'] (bot name) in reply, keep first response
        if (state['name2'] + ':') in reply:
            split = reply.split(state['name2'] + ':')
            if len(split) > 1:
                # Get first response after bot name
                reply = split[1]
                # If more replies start appearing, stop
                if len(split) > 2:
                    stop_found = True

            # Trim spaces
            reply = reply.strip()

        # HACK: If state['name1'] (user name) in reply, stop
        if (state['name1'] + ':') in reply:
            # Only return reply until the name
            reply = reply.split(state['name1'] + ':')[0]
            # Trim spaces
            reply = reply.strip()
            stop_found = True

        if stop_found or shared.stop_everything:
            break

        yield reply

    yield reply


def get_max_prompt_length(state):
    return state['max_new_tokens']


def generate_reply_wrapper(question, state, stopping_strings=None):
    """
    Returns formatted outputs for the UI
    """
    reply = question if not shared.is_seq2seq else ''
    yield formatted_outputs(reply, shared.model_name)

    for reply in generate_reply(question, state, stopping_strings, is_chat=False, escape_html=True):
        if not shared.is_seq2seq:
            reply = question + reply

        yield formatted_outputs(reply, shared.model_name)


def formatted_outputs(reply, model_name):
    return html.unescape(reply), generate_basic_html(reply)

def fix_galactica(s):
    """
    Fix the LaTeX equations in GALACTICA
    """
    s = s.replace(r'\[', r'$')
    s = s.replace(r'\]', r'$')
    s = s.replace(r'\(', r'$')
    s = s.replace(r'\)', r'$')
    s = s.replace(r'$$', r'$')
    s = re.sub(r'\n', r'\n\n', s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s


def stop_everything_event():
    shared.stop_everything = True


def generate_reply_mlc(question, original_question, state, stopping_strings=None, is_chat=False):
    shared.model.reset_chat(chat_config=mlc_model_config)  # Reset as we handle history, also to set settings
    t0 = time.time()
    raw_output = ''
    try:
        if not is_chat:
            yield ''

        if not state['stream']:
            result = shared.model.generate(prompt=question)
            yield result
        else:
            shared.model._prefill(input=question)
            i, new_msg = 0, ''
            while not shared.model._stopped():
                shared.model._decode()
                if i % 2 == 0 or shared.model._stopped():
                    new_msg = shared.model._get_message()
                    raw_output = new_msg
                    yield new_msg
                i += 1

    except Exception:
        traceback.print_exc()
    finally:
        t1 = time.time()
        print(f'Output generated in {(t1 - t0):.2f} seconds. Stats: {shared.model.stats()}')
        print(f"\nRAW OUTPUT:\n{raw_output}\n")
        return
