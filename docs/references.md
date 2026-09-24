# lollm

Model I want to run locally:
https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF

Example of low-mid range setup:
- GeForce 3060 TI 8Gb (NVIDIA Studio drivers)
- RAM: 32Gb
- CPU: AMD 5800X3D (8 physical cores)
- Storage: 1TB NVMe drive.


Unsure about the parameters, but here's an example that is supposed to work with 12Gb of VRAM: unsloth/Qwen3.8-Flash-Next-GGUF (UD-IQ3_XXS, 82 GB)

I want to start with a small context window as a POC/MVP.
The end goal is to run the model from VScode in a chat window.


Tools/tips for low VRAM installations:
https://github.com/GenerelSchwerz/llama.cpp/wiki
https://github.com/GenerelSchwerz/llama.cpp/wiki/Hardware-Setup-Guides
https://github.com/GenerelSchwerz/llama.cpp/wiki/8GB-VRAM-Setup

