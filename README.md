# AutoTasks

AutoTasks is a Discord Bot based program that allows content creators to look up their latest content / livestreams and then let their community know that its up / live!

*There currently no linux binaries supplied*


## Search Rates
Due to the fact that some / most of these serivces have rate limits and half-paid apis I have manually set these limits to try and prevent a constant Rate Limit message.
YouTube: 1 check per 10 Min
TikTok 1 check per 2 Min 30 Sec
Twitch 1 check per 2 Min 30 Sec
Twitter / X 1 check per 2 Min 30 Sec


## Don't trust the program?
Here is the VirusTotal link for the latest version:
https://www.virustotal.com/gui/file/be92865fcd6b896f7719e7258cc1f0249d6665656fa911b555cd3291c3ac2e93
*I know that VirusTotal isn't fool proof but It's sort of reliable for the most part*


## How do I edit the source?
1. You can download the project using git or download the source zip from github.
2. Edit the app.py file in your editor of choice. ( The launch.py file is used for launching the program and can be modified )
3. Please make sure that the .env file is the one that does not include your info if you plan on sharing it.
4. After your changes have been made you can use compile.bat to compile the code into an EXE file.


## What imports do I need?
The imports are listed in the `requirements.txt` file and can be easily installed using 
```bash
python -m install -r requirements.txt
```
Or here is a complete list ( versions not included )
- discord
- requests
- dotenv
- pyyaml
- feedparser
- selenium
- TikTokApi
- cython
- pyinstaller

However the EXE itself only imports
- discord
- requests
- dotenv
- pyyaml
- feedparser
- TikTokApi
- selenium
- requests_toolbelt
- aiohttp
