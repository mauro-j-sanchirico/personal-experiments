# PyDeriveHelper

`pyderivehelper` is a set of Python tools for performing mathematical calculations using Wolfram Language in a Jupyter notebook. Interfaces are provided for entering Wolfram Code directly and via natural language descriptions through OpenAI API calls.

## Description

## Dependencies

### Shell

A bash or bash-like shell is recommended. [`bash-git-prompt`](https://github.com/magicmonty/bash-git-prompt) is recommended for Windows. `bash-git-prompt` also ships with [`git`](https://git-scm.com/) by default.

### Wolfram Engine

The latest version of the [Wolfram Engine](https://www.wolfram.com/engine/) is required.

If Wolfram Engine is already installed, the current version can be checked via bash.

```bash
wolframscript -code '$VersionNumber'
```

If installing for the first time, the site will require setting up a license. The free license is sufficient for personal or prototype projects. Other licenses may be required for other use cases.

### OpenAI

An OpenAI account and token is required. A token can be obtained from [OpenAI](https://platform.openai.com/). Log in to the platform or create an account if needed.

Though it is not required, it is recommended to create a personal organization and personal project name.

1. Go to **`Projects` &rarr; `+ Create`**
2. Create a project called "Personal Math Assistant" (or something similar).

Now add tokens.

1. Go to **`Billing` &rarr; `Add to credit balance`**.
2. Buy desired amount of tokens.

Generate an API key.

1. Generate an API key with **`API Keys` &rarr; `Create new secret key`**.
2. Choose your token name and project.
3. Save the key obtained in a secure location.

## Installation

## Usage

## License

This project is provided with an MIT license (see `LICENSE` file). Additional dependencies have their own licenses which might apply depending on use case.

### Wolfram Engine

For Wolfram Engine, see the [license FAQ](https://www.wolfram.com/engine/faq/).

## Contributing