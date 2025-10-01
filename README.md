# 📺 Community Channel 99

*"Like public access TV, but for your own hard drive."*  

Community Channel 99 is a small Flask app that turns folders of video files into a local TV station.  
Shows play in a fixed schedule, synced to real time, so whenever you tune in, you’re seeing what’s currently “on air.”  

---

## ❓ Why

This isn’t meant to replace streaming services or proper video-on-demand.  
Sometimes you don’t know what you want to watch — you just want *something* on.  

Community Channel 99 is built for those kinds of shows and movies:  
- ones you can watch out of order,  
- ones you’ve already seen and love,  
- background comfort TV.  

If you want to binge the new season of *The Pitt*, this isn’t the best way to do it.  
If you just want to “flip channels” and land on *The Simpsons* or a random old movie, this scratches that itch.  

---

## 🚀 Quick Start

```bash
# 1. Clone this repo
git clone https://github.com/alexandersshen/community-channel-99.git
cd community-channel-99

# 2. Install requirements
pip install flask
brew install ffmpeg    # or apt install ffmpeg on Linux

# 3. Run the server
python app.py

# 4. Open in browser
http://localhost:5050
```

---

## ✨ Features

- Back-to-back shows that never stop.  
- Synced playback: refresh or reconnect and you land in the same spot.  
- Metadata panel with filename, format, duration, bitrate, and progress %.  
- “Now Playing” + “What’s Next” indicators.  
- Channels can be sequential or randomly shuffled once.  
- Optional commercials interleaved between shows.  
- Remote-style quick links to jump between channels.  
- Runs locally on your network — works on desktops, phones, and tablets.  

---

## 🛠 Requirements

- Python 3.9+  
- [ffmpeg](https://ffmpeg.org/) (with ffprobe) in your PATH  
- Python packages:  
  - Flask  

---

## 📂 Project Structure

```
community-channel-99/
│
├── app.py             # Flask server
├── channels.json      # channel definitions
├── static/            # CSS, images
├── templates/         # HTML templates
└── media/
    ├── simpsons/      # example channel folder
    │    ├── episode1.mp4
    │    └── episode2.mp4
    ├── cartoons/
    └── commercials/   # optional ad breaks
```

---

## 📺 Channel Setup

Channels are defined in **channels.json**:

```json
[
  {
    "id": "simpsons",
    "name": "The Simpsons",
    "path": "media/simpsons",
    "rotation": "sequential",
    "commercials": false
  },
  {
    "id": "cartoons",
    "name": "Cartoons",
    "path": "media/cartoons",
    "rotation": "random",
    "commercials": true
  },
  {
    "id": "commercials",
    "name": "Commercials",
    "path": "media/commercials",
    "rotation": "random",
    "commercials": false
  }
]
```

- `id`: short unique name  
- `name`: what shows in the UI  
- `path`: folder inside `media/` containing video files  
- `rotation`:  
  - `"sequential"` → plays in order  
  - `"random"` → shuffled once and then fixed  
- `commercials`:  
  - `true` → interleave ads from `media/commercials`  
  - `false` → shows only, no ads
  - this folder is required to append commercials between programs, so make sure there are files in here for that feature to work  

---

## 🚀 Running

Start the server:

```bash
python app.py
```

By default it runs on port **5050**.  

Access in your browser:

- On your computer:  
  `http://localhost:5050`

- On another device in the same network:  
  Find your local IP (Mac example):  
  ```bash
  ipconfig getifaddr en0
  ```  
  then open:  
  `http://192.168.x.x:5050`

---

## 💡 Notes

- Make sure your videos are encoded with **H.264 video + AAC audio**. Browsers don’t reliably play E-AC3 audio.  
- Long filenames are fine, but shorter names look cleaner in the “Now Playing” display.  
- This is meant for **local/LAN use**. It will run on a public server, but for real streaming you’d want HLS/DASH and a CDN.  

---

## 📜 License

This project is **open source** under the MIT license.  
Fork it, remix it, share it — just like a true community access channel.  
