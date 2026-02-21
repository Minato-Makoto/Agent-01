# [■] AGENT-01: SOFTWARE USER GUIDE

Welcome to the Agent-01 User Guide. This document provides technical instructions on installing, configuring, and operating an Open-source AI Agent. Agent-01 is an open-source foundational software application designed to run locally on personal computers, enabling developers and end-users to automate web browsers, execute terminal commands, manage local files, and decompose complex user requests into actionable sequential steps.

The primary executable script for initializing the application on Windows operating systems is: `run.bat`.

---

## [►] SECTION 1: SYSTEM STARTUP

To begin using the software, please follow these initialization steps:

1. Open a `cmd` or `PowerShell` window at the root directory containing the application's source code.
2. Launch the script by entering the following command:
   ```cmd
   run.bat
   ```
   
**Startup Initialization Process:**
- The application automatically creates an isolated working directory (sandbox) named `workspace`.
- It verifies required Python dependencies and automatically installs them if missing.
- It boots the local `llama-server` (if utilizing a `.gguf` model file) or establishes a connection to a configured remote API service.
- The application enters a complete ready state, waiting for your input.

---

## [►] SECTION 2: CONFIGURATION PARAMETERS

You can adjust various settings based on your usage requirements. The `run.bat` file acts as the primary configuration repository. Users can edit these values directly within the file using a text editor (like Notepad), or override them via the command line prior to execution:

`set MAX_TOKENS=8192 && run.bat`

### 2.1 AI Execution Environment (`PROVIDER`)
The core reasoning engine can process tasks locally on your computer or via cloud services.

*   **LOCAL MODE (Default):**
    *   **Configuration:** `set PROVIDER=local`
    *   **Characteristics:** Optimizes data privacy by utilizing your personal computer's hardware. Requires a pre-downloaded `.gguf` model and its absolute file path defined in the `MODEL_PATH` variable.
    *   **Performance Optimization:** Set `GPU_LAYERS=-1` to offload the neural network computation to your graphics card's Video RAM (VRAM), significantly optimizing response speed.

*   **REMOTE MODE:**
    *   **Configuration:** `set PROVIDER=openai_compatible`
    *   **Characteristics:** Leverages the computing power of third-party APIs (e.g., OpenAI, Anthropic). Users must provide `BASE_URL`, `MODEL_ID`, and configure an environment variable containing the API key (`API_KEY_ENV`).
    *   **Performance Optimization:** Suitable for complex logical workflows that exceed the capabilities of local hardware.

### 2.2 Inference Parameter Tuning
Adjust the AI's processing parameters to enhance the structural quality of outputs.

*   `CTX_SIZE`: The maximum context window size (in tokens) for a session. It is recommended to increase this value (e.g., to `16384`) when supplying continuous context files or large source code directories.
*   `TEMPERATURE`: Adjusts the consistency and determinism of the output text.
    *   `0.1`: Yields highly accurate results strictly adhering to structured data. Optimal for coding, variable configuration, and script-based logic generation.
    *   `0.7`: Increases variance for open-ended queries. Suitable for software design analysis and conceptual brainstorming.
*   `MAX_TOKENS`: The absolute ceiling for token generation during a single output frame. A value like `8192` prevents text files from being abruptly truncated during generation.

---

## [►] SECTION 3: SECURITY OPTIONS & SAFE ENVIRONMENTS

Because an Open-source AI Agent has the ability to run automated command-line prompts, we enforce strict security configurations to prevent unintended modifications to root system files.

*   **Default Sandbox Environment (`SHELL_WORKSPACE_ONLY`):**
    *   The default value is `1`. The application is restricted to a specifically configured directory: file modifications and shell commands are forced to operate entirely within the `./workspace` folder.
    *   **Important Notice:** Setting this value to `0` completely disables the isolation mechanism, allowing the application to execute commands path-wide on your device. Enable this only in a highly confident device environment.
*   **Automatic Circuit Breaker (`MAX_ITERATIONS` & `MAX_REPEATS`):**
    *   Prevents the software from entering infinite background execution loops. `MAX_ITERATIONS=25` ensures the runtime immediately halts if the task sequence fails to resolve after 25 consecutive interactive steps between the AI models and internal components.

---

## [►] SECTION 4: STANDARD PROMPTING GUIDELINES

Communicating with structured AI Agent software requires different prompt construction than standard conversational Chatbots. Input commands should clearly define the overarching goal accompanied by step-by-step sequential actions.

### [!] Unoptimized Format (Better Suited for Chatbots)
> "Write a Python script to track the price of crypto."

### [★] Standard Format (Optimized for Agent Frameworks)
> "Goal: Build a local Crypto price tracker application.
> 1. Use the web browser feature to navigate to `coinmarketcap.com`.
> 2. Analyze the DOM elements to extract the node containing real-time Bitcoin price data.
> 3. Program a Python extraction module that writes this variable to a file named `crypto.py` in the workspace directory.
> 4. Execute the module via the bash shell console and verify that the output behaves as expected."

**Why is this standard?** By providing a clear logical blueprint, the Open-source AI Agent sequentially engages its interconnected internal mechanisms (Browser Interface - File Write Access - Target Execute Access). It autonomously produces the logic, executes the software, and validates the output sequence prior to concluding the interaction.

The application successfully loaded. Awaiting response.
