import os
import argparse
import fnmatch
import subprocess
import time
import pandas as pd
import csv

import gspread
from pydub import AudioSegment
from pydub.silence import split_on_silence


def get_child_directories(directory_path):
    return [os.path.join(directory_path, name) for name in os.listdir(directory_path) if
            os.path.isdir(os.path.join(directory_path, name))]


def create_directory(input_dir, output_dir):
    input_dir_name = os.path.basename(os.path.normpath(input_dir))
    new_dir_path = os.path.join(output_dir, input_dir_name)
    os.makedirs(new_dir_path, exist_ok=True)
    print(f'Created directory {new_dir_path}')
    return new_dir_path


def find_m4a_files(directory_path, include_subdirs=False):
    m4a_files = []

    for root, dirnames, filenames in os.walk(directory_path, ):
        for filename in fnmatch.filter(filenames, '*.m4a'):
            relative_path = os.path.relpath(os.path.join(root, filename), directory_path)
            if include_subdirs or root == directory_path:
                m4a_files.append(relative_path)

    return m4a_files


def create_wav_file(dir_with_zoom, output_dir, m4afile):
    print('Creating wav file')

    m4a_dir, m4a_filename = os.path.split(m4afile)
    wav_filename = os.path.splitext(m4a_filename)[0] + '.wav'
    output_dir_path = os.path.join(output_dir, m4a_dir)
    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path)

    output_file_path = os.path.join(output_dir_path, wav_filename)
    if os.path.isfile(output_file_path):
        print('WAV file was already created')
        return output_file_path

    zoom_m4a_file = os.path.join(dir_with_zoom, m4afile)
    sound = AudioSegment.from_file(zoom_m4a_file, format='m4a')  # load source
    print(f'Removing silence')
    start_time = time.time()
    chunks = split_on_silence(sound, silence_thresh=-50, min_silence_len=3000)

    non_silent_audio = AudioSegment.empty()
    silence = AudioSegment.silent(duration=2000)

    for chunk in chunks:
        non_silent_audio += chunk
        non_silent_audio += silence

    end_time = time.time()
    print(f'Removed silence by time {end_time - start_time}')

    non_silent_audio = non_silent_audio.set_channels(1)  # mono
    non_silent_audio = non_silent_audio.set_frame_rate(16000)  # 16000Hz
    non_silent_audio.export(output_file_path, format="wav")
    print('Converted to wav')

    return output_file_path


def call_whisper(whisper, model, wavfile):
    if os.path.isfile(wavfile + '.txt'):
        print('Transcription already was created')
        return

    command = [
        whisper,
        "-t", "8",
        "-m", model,
        "--language", "russian",
        "-ocsv",
        "-otxt",
        "-f", wavfile
    ]

    print(f'Converting to text')
    start_time = time.time()
    subprocess.run(command, check=True)
    end_time = time.time()
    print(f'Converted to text by time {end_time - start_time}')


def create_google_doc(dir_with_zoom, wav_file):
    gc = gspread.service_account(filename=r'f:\Downloads\zoom2text-a4734ed30264.json')
    last_dir = os.path.basename(os.path.normpath(dir_with_zoom))
    sheet_name = f'Zoom2Text {last_dir}'

    try:
        spreadsheet = gc.open(sheet_name)
    except gspread.SpreadsheetNotFound:
        spreadsheet = gc.create(sheet_name)
        res = spreadsheet.share('podlesniy@gmail.com', perm_type='user', role='writer', notify=True)
        permission_id = res.json()["id"]
        spreadsheet.transfer_ownership(permission_id)

    data = pd.read_csv(f'{wav_file}.csv', escapechar="\\")
    file_name = os.path.splitext(os.path.basename(wav_file))[0]

    try:
        spreadsheet.worksheet(file_name)
        print(f'Worksheet {file_name} already created')
        return
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(file_name, 1, 100)

    worksheet.insert_rows(data.values.tolist(), 1)
    try:
        worksheet0 = spreadsheet.worksheet('Sheet1')
        spreadsheet.del_worksheet(worksheet0)
    except gspread.WorksheetNotFound:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List child directories of a given directory")
    parser.add_argument("-pz", "--pathZoom", type=str, help="The path to the Zoom directory")
    parser.add_argument("-po", "--pathOutput", type=str, help="The path to the Output directory")
    parser.add_argument("-wh", "--whisper", type=str, help="Whisper main")
    parser.add_argument("-m", "--model", type=str, help="Whisper model")
    args = parser.parse_args()

    zooms = get_child_directories(args.pathZoom)
    for dir_with_zoom in zooms:
        print(f'Processing zoom directory {dir_with_zoom}')
        output_dir = create_directory(dir_with_zoom, args.pathOutput)
        m4a_files = find_m4a_files(dir_with_zoom, True)
        for m4a_file in m4a_files:
            print(f'Processing m4a {m4a_file}')
            wav_file = create_wav_file(dir_with_zoom, output_dir, m4a_file)
            call_whisper(args.whisper, args.model, wav_file)
            create_google_doc(dir_with_zoom, wav_file)
