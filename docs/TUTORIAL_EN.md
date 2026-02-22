# [■] Agent-01: Offline Agent User Guide

Welcome to the Agent-01 User Guide! This guide will help you install, configure, and operate your very own Offline AI Agent.

Agent-01 is a project designed to run **100% offline** directly on your Windows PC, empowering your computer with an LLM to: use web browsers, operate the Adobe Suite, execute system commands, manage files, and process your requests via natural language communication... all without requiring an internet connection!
The application runs on the Windows OS by executing the `run.bat` file.

---

## [+] Section 1: System Startup

Download **llama-server.exe** at: https://github.com/ggml-org/llama.cpp/releases and extract it to the `llama-server` directory of the project.
Configure the necessary parameters in the `run.bat` file using Notepad or similar software, save it, and double-click the `run.bat` file to start.
The system will automatically check and install the required libraries if your machine doesn't have them yet (This is the only part that requires internet).

---

## [*] Section 2: Configuration Parameters

You can easily customize Agent-01 to fit your needs. The `run.bat` file stores the primary configurations. You can open and edit this file using code editors (like Notepad), or temporarily override parameters directly when typing commands in the terminal, for example:

`set MAX_TOKENS=8192 && run.bat`

The `run.bat` file contains comments and examples for each parameter so you can customize them to suit your computer's configuration.

### 2.1 Offline & Online Mode (`PROVIDER`)

*   **Offline mode (Default & Recommended):**
    *   **Setup:** `set PROVIDER=local` along with `MODEL_PATH=` being the path to the GGUF model on your computer.
    *   **Description:** This mode runs 100% offline using your device's hardware, utilizing open-source GGUF AI models.

*   **Online mode (Remote API):**
    *   **Setup:** `set PROVIDER=openai_compatible`
    *   **Description:** Used to call LLMs via APIs from providers such as OpenAI, Anthropic, Google...
    *   **API ENV Setup:**
        1. Press the Start button on your keyboard, type: env
        2. Select "Edit the system environment variables".
        3. When System Properties appears, click the "Environment Variables..." button at the bottom.
        4. In the User variables section, click the New... button.
        5. Fill in the following:
            Variable name: OPENAI_API_KEY
            Variable value: sk-12344566778... (Paste your exact API Key here).
        6. Click OK.

### 2.2 Fine-Tune the AI's Brain
Modify how the AI Agent thinks and generates text to achieve better output quality.

*   **`CTX_SIZE` (Memory Capacity):** The AI's short-term memory (in tokens). A high parameter (e.g., `16384`) is needed for the AI to read long documents and process complex requests.
*   **`TEMPERATURE` (Creativity):** Adjusts the creativity of the AI Agent in its responses (Low = logical/less creative, High = creative/many ideas).
    *   `0.1`: Highly logical, analytical, and extremely precise. Optimal for generating source code, declaring variables, or creating technical outlines.
    *   `0.7`: Creative with a natural conversational tone. Best suited for discussions and brainstorming ideas.
*   **`MAX_TOKENS` (Output Length):** The maximum string length per model response. Parameters like `8192` might still experience text truncation or stop responding for very long outputs.

---

## [!] Section 3: Security & Safe Environments

Because the Offline Agent has the ability to run commands on your computer, it comes with strict protection mechanisms to ensure the AI doesn't accidentally destroy your system.

*   **Default sandbox (`SHELL_WORKSPACE_ONLY`):**
    *   Always set to `1` by default. Your assistant is locked in a safe operating space. Any file modification commands or shell scripts are forced to run only inside the `./workspace` directory.
    *   **[!] Warning:** Changing this value to `0` disables the sandbox, allowing the AI to access and modify file names across the entire computer.
*   **Anti-loop (`MAX_ITERATIONS` & `MAX_REPEATS`):**
    *   To prevent cases where the model creates an endless tool loop, `MAX_ITERATIONS=60` ensures the system automatically terminates if the model calls tools 60 times consecutively. (Increase this if you need to generate many files and can estimate the model's tool usage).

---

## [>] Section 4: Communicating with the AI Agent

The AI Agent's response deeply relies on the model you chose to use; the system only provides the tools and environment for the LLM to evolve into an AI Agent.
It works well with 4B-8B models intended for mid-range computers (Intel i7, 32GB RAM, RTX 3070ti).

---

## [>] Section 5: LLM Download
You can find and download GGUF models at: https://huggingface.co/

---

## [>] Section 6: Personalizing the Agent (users & developers)
*   **User:** 
    *   The `SOUL.md` and `USER.md` files are where you personalize the Agent. 
    *   `SOUL.md`: Where you set the Agent's personality, role, behavioral rules, and conduct.
    *   `USER.md`: Where you enter your personal information, helping the Agent understand and serve you better.
*   **Developer:** 
    *   For developers, anyone can fork the project and further develop or rewrite the entire source code using an AI CLI on IDEs like VSCode, Antigravity, etc.
    *   The same goes for the skill set; download or write your own `SKILL.md` file and tell the AI CLI to register the skill for Agent-01. This is how the project avoids unwanted prompt injection for the Agent.

---

## [Ω] A Note from the Creator:
This project was created 100% by an AI Generator, so there are inevitably flaws. The project will continue to be improved gradually depending on my free time, OR YOU YOURSELF WILL BE THE ONE TO COMPLETE IT. Do not hesitate to use this project as a modular tool. Because the code was written by AI, the AI can completely read and understand the code. Ask it to find out what even its creator doesn't know. Good luck, and have fun playing this 2026 AI game!
Thanks & Best Regards,
Minato.
https://minato-makoto.github.io 
