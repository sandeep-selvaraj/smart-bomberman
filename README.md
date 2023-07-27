# smart-bomberman ![GitHub release](https://img.shields.io/github/release/sandeep-selvaraj/smart-bomberman?include_prereleases=&sort=semver&color=blue)[![Pylint](https://github.com/sandeep-selvaraj/smart-bomberman/actions/workflows/pylint.yml/badge.svg)](https://github.com/sandeep-selvaraj/smart-bomberman/actions/workflows/pylint.yml) [![mypy](https://github.com/sandeep-selvaraj/smart-bomberman/actions/workflows/mypy.yml/badge.svg?branch=master)](https://github.com/sandeep-selvaraj/smart-bomberman/actions/workflows/mypy.yml)
<a href="https://github.com/sandeep-selvaraj/smart-bomberman/blob/master/LICENSE">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-yellow">
</a>
<a href="https://tu-dresden.de/?set_language=en">
  <img alt="Static Badge" src="https://img.shields.io/badge/Technical University-Dresden-blue">
</a>

<a href="https://imld.de/en/">
  <img alt="Static Badge" src="https://img.shields.io/badge/Faculty-IMLD-green">
</a>

### Visual Computing Team Project 2023

[![](https://dcbadge.vercel.app/api/server/CpHsfRzCk)](https://discord.gg/CpHsfRzCk)

Released under [MIT](/LICENSE). 

## Table of contents

- [Installation](#installation-of-package)
- [Run the game](#to-start-the-game)
- [How to play the game](#game-controls)
- [Information of the AI agents](#information-of-the-ai-agents)
- [Note on problems](#note-to-keep-in-mind-for-untracked-or-potenital-issues)
- [Documentation](#documentation)

### Installation of package
`pip install -e .` 

_(Tip: Do it in your virtual environment)_


### To start the game

run `smart-bomberman` in your terminal

### Game controls
- Arrow keys to move
- 'X' to place bomb


### Information of the AI agents
### Following branches can be explored for the different AI agents built for this team project

- _feature/divyendu_ : Multiple observation space related PPO and NEAT models that fuel the AI agent
- _feature/ken_ : Multiple Observation spaces PPO with curriculum learning path taken
- _feature_juhyun_ : Dict Observation space and best working model for AI agent
- _feature/sandeep_ : Box Observation space - "Redundant and maybe be improved"
- _training/sandeep_ : Multiplayer for visual benchmarking and visualization of training processes

### Note to keep in mind for untracked or potenital issues

- **Only for Non-MacOs users**: For using GPUs while training it's required that after installation
`pytorch` is uninstalled and the stable version which supports
`CUDA > 11.7` is installed from [pytorch](https://pytorch.org/)
  - For Linux and Windows, run this command: `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`
  - For Mac, the default package should be alright. 
- Follow the requisite instructions for each branch and be careful with `gymnasium` and `stable-baselines` libraries. 

### Documentation

Please check out the [official documentation](https://cloudstore.zih.tu-dresden.de/index.php/s/f5Dr3pppn6ySrcp) 
pertaining all the key aspects of research and development of the smart-bomberman.