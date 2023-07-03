import os
import argparse
import fnmatch
import subprocess


def get_child_directories(directory_path):
    return [os.path.join(directory_path, name) for name in os.listdir(directory_path) if
            os.path.isdir(os.path.join(directory_path, name))]


def create_directory(input_dir, output_dir):
    input_dir_name = os.path.basename(os.path.normpath(input_dir))
    new_dir_path = os.path.join(output_dir, input_dir_name)
    os.makedirs(new_dir_path, exist_ok=True)
    return new_dir_path


def find_m4a_files(directory_path):
    m4a_files = []

    for root, dirnames, filenames in os.walk(directory_path):
        for filename in fnmatch.filter(filenames, '*.m4a'):
            relative_path = os.path.relpath(os.path.join(root, filename), directory_path)
            m4a_files.append(relative_path)

    return m4a_files


def create_wav_file(dir_with_zoom, output_dir, m4afile):
    m4a_dir, m4a_filename = os.path.split(m4afile)

    zoom_m4a_file = os.path.join(dir_with_zoom, m4afile)
    wav_filename = os.path.splitext(m4a_filename)[0] + '.wav'
    output_dir_path = os.path.join(output_dir, m4a_dir)
    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path)

    output_file_path = os.path.join(output_dir_path, wav_filename)

    command = ["ffmpeg", "-i", zoom_m4a_file, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", output_file_path]
    if not os.path.isfile(output_file_path):
        print('Converting to wav')
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print('Converted to wav')
    else:
        print('Already converted to wav')

    return output_file_path


def call_whisper(whisper, model, wavfile):
    command = [
        whisper,
        "-m", model,
        "-t", "16",
        "-l", "ru",
        "-otxt",
        "-osrt",
        "-ocsv",
        "-ovtt",
        "-pp",
        "-f", wavfile
    ]

    print(f'Converting to text')
    #subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    subprocess.run(command, check=True)
    print(f'Converted to text')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List child directories of a given directory")
    parser.add_argument("-pz", "--pathZoom", type=str, help="The path to the Zoom directory")
    parser.add_argument("-po", "--pathOutput", type=str, help="The path to the Output directory")
    parser.add_argument("-wh", "--whisper", type=str, help="Whisper main")
    parser.add_argument("-m", "--model", type=str, help="Whisper model")
    args = parser.parse_args()

    zooms = get_child_directories(args.pathZoom)
    for dir_with_zoom in zooms:
        print(f'Processing {dir_with_zoom}')
        output_dir = create_directory(dir_with_zoom, args.pathOutput)
        print(f'Created {output_dir}')
        m4a_files = find_m4a_files(dir_with_zoom)
        for m4a_file in m4a_files:
            print(f'Processing {m4a_file}')
            wav_file = create_wav_file(dir_with_zoom, output_dir, m4a_file)
            call_whisper(args.whisper, args.model, wav_file)

