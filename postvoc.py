#!/usr/bin/env python

import sys
import subprocess
import re

def get_language_code(filename):
    match = re.search(r'-(\w{3})\.\w+$', filename)
    if match:
        return match.group(1)
    else:
        return None

def main():
    if len(sys.argv) < 3:
        print("Usage: python script.py [video_file] [audio_files...] [--force]")
        return

    video_file = sys.argv[1]
    audio_files = []
    force_flag = False

    for arg in sys.argv[2:]:
        if arg == "--force":
            force_flag = True
        else:
            audio_files.append(arg)

    # Get existing audio streams with their language codes from the video file
    ffprobe_command = ["ffprobe", "-v", "error", "-show_entries", "stream=index:stream_tags=language", "-select_streams", "a", "-of", "default=noprint_wrappers=1", video_file]
    ffprobe_output = subprocess.check_output(ffprobe_command, universal_newlines=True)

    existing_audio_streams = {}  # Map of stream index to language code
    lines = ffprobe_output.strip().split('\n')
    for line in lines:
        parts = line.split('=')
        if parts[0] == 'index':
            stream_index = int(parts[1])
        elif parts[0] == 'TAG:language':
            lang = parts[1].strip()
            existing_audio_streams[stream_index] = lang

    # Check if any of the new audio languages already exist unless force_flag is set
    new_audio_streams = {}
    for audio_file_index, audio_file in enumerate(audio_files):
        audio_language = get_language_code(audio_file)
        if audio_language in existing_audio_streams.values() and not force_flag:
            print(f"The language {audio_language} already exists in the master video. Use --force to override.")
            return
        new_audio_streams[audio_file_index] = {"file": audio_file, "lang": audio_language}

    print(f"Video file {video_file} has existing audio streams: {existing_audio_streams}")
    print(f"New audio streams to add or replace: {new_audio_streams}")

    # Construct the ffmpeg command: Load video file as input #0
    ffmpeg_command = ["ffmpeg", "-i", video_file]
    # And map video from input #0 to output
    stream_args = ["-map", "0:v"]
    
    # map all existing audio streams unless we want to overwrite one
    for stream_index, lang in existing_audio_streams.items():
        if lang in [get_language_code(audio_file) for audio_file in audio_files]:
            stream_args.extend(["-map", f"{stream_index}:a:0"])
            stream_args.extend([f"-metadata:s:a:{stream_index}", f"language={lang}"])
        else:
          stream_args.extend(["-map", f"0:{stream_index}"])

    new_stream_index = max(existing_audio_streams.keys(), default=-1) + 1
    for audio_file_index, audio_file in enumerate(audio_files):
        audio_language = get_language_code(audio_file)
        if audio_language not in existing_audio_streams.values():
          # replacing existing languages already happened above
          ffmpeg_command.extend(["-i", audio_file])
          stream_args.extend(["-map", f"{audio_file_index+1}:a:0"])
          stream_args.extend([f"-metadata:s:{new_stream_index}", f"language={audio_language}"])
          new_stream_index += 1

    final_command = (
        ffmpeg_command +
        stream_args +
        ["-c", "copy", "-y", "output.mp4"]
    )

    print(' '.join(final_command))
    # ffmpeg -i camp2023-57571-deu-Jens_Spahns_credit_score_is_very_good_sd.mp4 -i camp2023-57571-deu-Jens_Spahns_credit_score_is_very_good_opus-eng.opus -map 0:v:0 -map 0:a:0 -c copy -metadata:s:a:1 language=eng -y output.mp4
    # Run the ffmpeg command
    #subprocess.call(final_command)

if __name__ == "__main__":
    main()
