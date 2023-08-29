#!/usr/bin/env python

import os
import re
import subprocess
import sys


iso3cc_to_language = {
    'eng': 'English',
    'deu': 'Deutsch',
    'fra': 'Français',
    'spa': 'Español',
    'ita': 'Italiano',
    'por': 'Português',
    'nld': 'Nederlands',
    'swe': 'Svenska',
    'fin': 'Suomi',
    'dan': 'Dansk',
    'nor': 'Norsk',
    'pol': 'Polski',
    'ces': 'Čeština',
    'hun': 'Magyar',
    'ron': 'Română'
}


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
    dry_run_flag = False

    for arg in sys.argv[2:]:
        if arg == "--force":
            force_flag = True
        elif arg == "--dry-run":
            dry_run_flag = True
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

    # Map input file index to languages/files
    new_audio_streams = []
    for audio_file_index, audio_file in enumerate(audio_files):
        audio_language = get_language_code(audio_file)
        if audio_language is None:
            print(f"Audio language could not be determined for file '{audio_file}'. Name the file foobar-CC3.ext where CC3 is an ISO 3-letter language code.")
            return
        new_audio_streams.append(audio_language)

    print(f"Video file {video_file} has existing audio streams: {existing_audio_streams}")
    print(f"New audio streams to add or replace: {new_audio_streams}")

    # Check if any of the new audio languages already exist unless force_flag is set
    for audio_language in new_audio_streams:
        if audio_language in existing_audio_streams.values() and not force_flag:
            print(f"The language {audio_language} already exists in the master video. Use --force to override.")
            return

    # Construct the ffmpeg command: Load video file as input #0
    ffmpeg_command = ["ffmpeg", "-i", video_file]
    # And map video from input #0 to output copying (not re-encoding)
    stream_args = ["-map", "0:v", "-c:v", "copy"]
    # Map metadata from original only
    stream_args.extend(["-map_metadata", "0"])
    
    # map all existing audio streams unless we want to overwrite one
    for stream_index, lang in existing_audio_streams.items():
        if lang in new_audio_streams:
            audio_file_index = new_audio_streams.index(lang)
            # map new audio file as stream
            stream_args.extend(["-map", f"{audio_file_index}:a:0"])
        else:
            # copy existing stream
            stream_args.extend(["-map", f"0:{stream_index}"])
            stream_args.extend([f"-c:{stream_index}", "copy"])

    new_stream_index = max(existing_audio_streams.keys(), default=-1) + 1
    for audio_file_index, audio_file in enumerate(audio_files):
        audio_language = get_language_code(audio_file)
        if audio_language not in existing_audio_streams.values():
            # replacing existing languages already happened above
            ffmpeg_command.extend(["-i", audio_file])
            i = audio_file_index + 1
            stream_args.extend(["-filter_complex", f"[{i}:a]compand=points=-20/-600|-18/-18[ta{i}];[ta{i}]asplit=2[sc{i}][mix{i}];[0:a][sc{i}]sidechaincompress=level_in=0.3:threshold=0.1:attack=50:release=2500[compr{i}];[compr{i}][mix{i}]amix[final{i}]"])
            stream_args.extend(["-map", f"[final{i}]"])
            stream_args.extend([f"-metadata:s:{new_stream_index}", f"language={audio_language}"])
            stream_args.extend([f"-metadata:s:{new_stream_index}", f"title={iso3cc_to_language.get(audio_language, audio_language)}"])
            new_stream_index += 1

    output_filename = os.path.splitext(video_file)[0] + '-out' + os.path.splitext(video_file)[1]
    final_command = (
        ffmpeg_command +
        stream_args +
        ["-y", output_filename]
    )

    print(' '.join(final_command))
    if not dry_run_flag:
      subprocess.call(final_command)
      print(f"Wrote {output_filename}")

if __name__ == "__main__":
    main()
