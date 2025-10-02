import os, json, time, random, subprocess
from functools import lru_cache
from flask import Flask, render_template, send_file, abort, jsonify
from datetime import datetime, timezone
import hashlib

app = Flask(__name__)

# Load channel config
with open("channels.json") as f:
    config = json.load(f)

# What channels in channels.json are gonna be there.
CHANNELS = config["channels"]

# Declare playlists - ultimately the programming schedule for each channel that gets looped forever
PLAYLISTS = {}

# Reference start time (aligns schedule)
START_TIME = datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp()

# Valid file extensions
VALID_EXTS = (".mp4", ".m4v", ".mov", ".avi", ".mkv")

# Cache results for up to 256 different files so we don't re-run ffprobe
# every single time (saves time if you ask about the same file a lot).
@lru_cache(maxsize=256)
def get_duration(filepath):
    """Return duration of a video file in seconds using ffprobe."""
    try:
        # Run ffprobe (part of ffmpeg) as a separate process.
        # We're asking it to only tell us the "duration" of the file,
        # and return that as plain text (no extra labels or wrappers).
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"ffprobe failed for {filepath}: {e}")
        return 22 * 60  # fallback 22 min because Simpsons episodes are ~22 minutes

def get_channel_files(channel):
    """Return sorted list of video files for a channel's main content only."""
    
    # Grab the folder path for this channel from its JSON definition
    # e.g. "media/simpsons"
    path = channel["path"]
    
    # If the folder doesn’t exist (maybe it was mis-typed),
    # just return an empty list so we don’t crash.
    if not os.path.exists(path):
        return []
        
    # Otherwise, build a list of files inside that folder:
    # 1. Look at everything in the folder (os.listdir).
    # 2. Sort the list alphabetically (so episode1, episode2, etc.).
    # 3. Only keep files that end with a valid video extension (VALID_EXTS).
    # 4. Prepend the full path to each file so we can find it later.
    return [
        os.path.join(path, f.strip())
        for f in sorted(os.listdir(path))
        if f.lower().endswith(VALID_EXTS)
    ]
    
# We want to shuffle the list of files (random order),
# BUT we also want the shuffle to be *stable* —
# meaning: given the same seed, the order will always come out the same.
# That way, "random channels" don't reshuffle every page refresh.
def stable_shuffle(files, seed):
    import hashlib
    
    # Take the seed (usually channel id), hash it with md5,
    # then turn that giant hex string into an integer.
    # This ensures that the "random" shuffle is always the same
    # for the same seed value.
    rng = random.Random(int(hashlib.md5(seed.encode()).hexdigest(), 16))
    
    # Copy the list so we don’t mess with the original order
    shuffled = files[:]
    
    # Shuffle it using our custom random generator (tied to the seed)
    rng.shuffle(shuffled)
    return shuffled

def build_playlist(channel):
    """Return full playlist for a channel, with optional commercials interleaved."""
    # Step 1: grab the main video files for this channel
    files = get_channel_files(channel)

    # Randomize or keep sequential
    # Step 2: figure out how to order them
    if channel.get("rotation") == "random":
        # If the channel says "random", shuffle once in a stable way
        # (so it’s consistent each time you tune in)
        files = stable_shuffle(files, channel["id"])
    else:
        # Otherwise just keep them in alphabetical/episode order
        files = sorted(files)

    # Step 3: commercials
    # By default commercials are ON unless explicitly set to false in JSON
    if channel.get("commercials", True):
        commercial_path = os.path.join("media", "commercials")
        commercials = []
        if os.path.exists(commercial_path):
            commercials = [
                os.path.join(commercial_path, f)
                for f in os.listdir(commercial_path)
                if f.lower().endswith(VALID_EXTS)
            ]

        # Step 4: interleave commercials after each episode
        playlist = []
        for ep in files:
            playlist.append(ep)
            if commercials:
                num_ads = random.randint(0, 2)  # choose 0, 1, or 2 ads
                chosen_ads = random.sample(commercials, k=min(num_ads, len(commercials)))
                playlist.extend(chosen_ads)
        return playlist

    # Step 5: if commercials are OFF, just return the shows by themselves
    return files

# Build once at startup
for ch in CHANNELS:
    PLAYLISTS[ch["id"]] = build_playlist(ch)

# =========== FOR DEBUGGING ================
# Print out the playlist in console (for debugging)
# This loops over every channel we defined     
# =========== FOR DEBUGGING ================
for ch in CHANNELS:
    # Get that channel’s playlist (list of shows + maybe commercials)
    files = PLAYLISTS.get(ch["id"], [])
    print(f"\n📺 Channel: {ch['name']} ({ch['id']})")
    
    # Go through each file in the playlist and print its position + name
    for i, f in enumerate(files, start=1):
        # i = index (1, 2, 3, …)
        # f = full filepath
        # os.path.basename(f) just gives the filename (without folders)
        print(f"  {i:02d}. {os.path.basename(f)}")
    
def get_now_playing(channel):
    # Grab the playlist for this channel
    files = PLAYLISTS.get(channel["id"], [])
    if not files:
        return None, 0, None, None

    # Figure out how long each video is
    durations = [get_duration(f) for f in files]
    total = sum(durations)  # total length of the entire playlist loop

    # Figure out how far into the "fake TV schedule" we are right now
    # (time since START_TIME, wrapped around the playlist length)
    elapsed = int(time.time() - START_TIME)
    elapsed %= int(total)

    # Walk through each file until we find the one that covers this time
    offset = elapsed
    for i, d in enumerate(durations):
        if offset < d:
            now_file = files[i]
            now_offset = int(offset)

            # Figure out what comes next
            # If there's only one file, "next" just loops back to it
            if len(files) > 1:
                next_index = (i + 1) % len(files)
                next_file = files[next_index]
            else:
                # If there’s only one file, “next” is just itself
                next_file = now_file

            # Figure out what *time* the next show will start
            time_until_next = d - offset
            start_time = time.strftime(
                "%-I:%M%p", time.localtime(time.time() + time_until_next)
            )

            # Return: current file, offset into it, next file, and when that starts
            return now_file, now_offset, next_file, start_time

        # Otherwise subtract this video’s duration and keep looking
        offset -= d

    # Fallback (shouldn’t usually hit this):
    # Just return the first file as current and next
    return files[0], 0, files[0], None

@app.route("/")
def index():
    # We'll build a list of channels + what's currently playing
    now = []
    
    # Loop through every channel defined in channels.json
    for c in CHANNELS:
        # Figure out what’s playing right now on this channel
        f, offset, next_file, next_time = get_now_playing(c)
        
        # Add a dictionary with the channel id, name,
        # and the current file’s name (just the filename, not full path).
        now.append({"id": c["id"], "name": c["name"], "file": os.path.basename(f) if f else "N/A"})
    
    # Render the index.html template and pass the list of channels in
    return render_template("index.html", channels=now)

def get_file_metadata(filepath):
    try:
        # Ask ffprobe (part of ffmpeg) for details about the file.
        # We only want: filename, format name, duration, and bitrate.
        # Output is JSON so it's easy to parse.
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=filename,format_name,duration,bit_rate",
                "-of", "json",
                filepath,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        # Parse the JSON result and grab the "format" section
        data = json.loads(result.stdout).get("format", {})

        # Clean up the filename so it looks nicer in the UI:
        # strip away folder paths and the extension
        if "filename" in data:
            base = os.path.basename(data["filename"]).strip()       # something like 'title.mp4'
            name, _ = os.path.splitext(base)                # title
            data["filename"] = name

        return data
    except Exception as e:
        # If ffprobe crashes or the JSON parse fails,
        # print an error and just return an empty dict
        print(f"ffprobe failed for metadata: {e}")
        return {}

@app.route("/watch/<channel_id>")
def watch(channel_id):
    # Look up the channel in our CHANNELS list using the given channel_id
    channel = next((c for c in CHANNELS if c["id"] == channel_id), None)
    if not channel:
        abort(404)

    # Figure out what’s currently playing on this channel
    # f = current file, offset = how far in we are,
    # next_file = what's coming up after this, next_time = when it starts
    f, offset, next_file, next_time = get_now_playing(channel)
    if not f:
        abort(404)
        
    # Make the file path relative to "media" so the browser can request it
    relpath = os.path.relpath(f, "media")
    
    # Grab metadata (name, duration, bitrate, etc.) for the current file
    metadata = get_file_metadata(f)
    
    # Also get the duration (used to sync playback position)
    duration = get_duration(f)

    # Finally, render the player.html template with everything it needs
    return render_template(
        "player.html",
        channel=channel,
        current_file=relpath,
        offset=offset,
        metadata=metadata,
        duration=duration,
        channels=CHANNELS,
        next_file=os.path.basename(next_file) if next_file else None,
        next_time=next_time,
    )

@app.route("/media/<path:filename>")
def media(filename):
    # Build the actual file path inside our "media" folder
    filepath = os.path.join("media", filename)
    
    # If the file doesn't exist, bail out with a 404...
    if not os.path.exists(filepath):
        abort(404)
        
    # Otherwise send the file back to the browser
    return send_file(filepath)
    
def get_next_show(channel, current_file):
    # Grab all the files for this channel
    files = get_channel_files(channel)
    if not files:
        return None
    try:
        # Find the position of the current file in the playlist
        idx = files.index(current_file)
        
        # Return the "next" one in the list,
        # wrapping back around to the first if we're at the end
        return files[(idx + 1) % len(files)]
    except ValueError:
        return files[0]
        
@app.route("/now/<channel_id>")
def now(channel_id):
    # Look up the channel by its ID (e.g. "simpsons")
    channel = next((c for c in CHANNELS if c["id"] == channel_id), None)
    if not channel:
        abort(404)

    # Ask: what's currently playing on this channel?
    # f = file path, offset = how many seconds into it we are,
    # next_file = what's playing after this, next_time = when it starts
    f, offset, next_file, next_time = get_now_playing(channel)
    if not f:
        abort(404)

    # Return a JSON response with all the sync info
    return {
        "file": os.path.relpath(f, "media"),    # path relative to /media
        "offset": offset,                       # how far into the file
        "duration": get_duration(f),            # total length in seconds
        "next_file": os.path.basename(next_file) if next_file else None,    # upcoming show
        "next_time": next_time,                 # when the next show starts
    }
    
@app.route("/metadata/<path:filename>")
def metadata(filename):
    # Build full file path
    filepath = os.path.join("media", filename)
    if not os.path.exists(filepath):
        abort(404)
    
    # Return metadata about the file as JSON
    return jsonify(get_file_metadata(filepath))

# ========== SETUP ON PORT 5050 ===============
# Run the Flask app on all interfaces so it's reachable
# across your local network, using port 5050
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
