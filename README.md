Twitch TTS with RVC Model

RVC files not included!

Rquirements:
- Python Installation: https://www.python.org/downloads/windows/
- Install needed python packages with pip
- Piper TTS: https://github.com/rhasspy/piper/releases -> unzip in the root folder
- Download TTS model: https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0/de/de_DE/thorsten/high -> put in root folder
- RVC: https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI -> Download rep as .zip -> unzip in RCV folder
- Twitch Token: https://twitchtokengenerator.com/ -> Bot Chat Token -> Access Token -> add in config.json file -> token
- Edit config.json -> temp_dir

Add RVC model:
- Add .pth files in folder RVC\assets\weights
- Add index file in folder RVC\logs

How to use:
- Start go-web.bat in RVC folder
- Start Twitch_TTS_RVC.py
- Choose RVC model in app
- Click Start
