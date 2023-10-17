# Text Generation Web UI - MLC-LLM fork

This is a HEAVILY gutted fork which only supports MLC-LLM backend.

## Installation

1. Create conda environment targeting Python 3.11 with `conda create -n textgen python=3.11`
2. Activate the environment with `conda activate textgen`
3. Install the packages from `Working Wheels` folder
4. Install rest of requirements with `pip install gradio markdown` (and other packages that error out)
5. Download MLC-LLM model(s) and place them in `models` folder
6. Run the server with `python server.py --model-menu`, choose your model by entering the number and press enter
7. Open the link in your browser and go at it!