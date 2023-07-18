import os
import argparse
import fnmatch
import openai
from pydub import AudioSegment


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


def transcribe(mp3_file):
    print(f'Converting to text')
    #return 'test'
    with open(mp3_file, "rb") as audio_file:
        return openai.Audio.transcribe(
            file=audio_file,
            model="whisper-1",
            response_format="srt"
        )


def save_to_file(mp3_file, transcript):
    transcribe_filename = mp3_file + '.srt'
    with open(transcribe_filename, 'w') as f:
        f.write(transcript)


def split(dir_with_zoom, m4a_file, output_dir):
    m4a_dir, m4a_filename = os.path.split(m4a_file)
    zoom_m4a_file = os.path.join(dir_with_zoom, m4a_file)
    chunk_filename = f'_chunk_{os.path.splitext(m4a_filename)[0]}.mp3'
    audio = AudioSegment.from_file(zoom_m4a_file, format='m4a')
    #tempfile = a

    # calculate the duration for the chunks
    duration_ms = len(audio)
    target_duration_ms = int(24*1024*1024 / os.path.getsize(zoom_m4a_file) * duration_ms)
    target_duration_ms = 60 * 60 * 1000

    # Split
    chunks = make_chunks(audio, target_duration_ms)

    output_dir_path = os.path.join(output_dir, m4a_dir)
    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path)

    chunk_files = []
    # Export chunks
    for i, chunk in enumerate(chunks):
        chunk_file_path = os.path.join(output_dir_path,f"{i}{chunk_filename}")
        chunk_files.append(chunk_file_path)
        chunk.export(chunk_file_path, format='mp3' )

    return chunk_files


def make_chunks(audio, chunk_duration_ms):
    """
    Breaks an audio file into chunks of a certain length
    """
    chunk_length = len(audio)
    chunks = []

    while chunk_length > chunk_duration_ms:
        chunks.append(audio[:chunk_duration_ms])
        audio = audio[chunk_duration_ms:]
        chunk_length -= chunk_duration_ms

    chunks.append(audio)

    return chunks

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List child directories of a given directory")
    parser.add_argument("-pz", "--pathZoom", type=str, help="The path to the Zoom directory")
    parser.add_argument("-po", "--pathOutput", type=str, help="The path to the Output directory")
    parser.add_argument("-wh", "--whisper", type=str, help="Whisper main")
    parser.add_argument("-m", "--model", type=str, help="Whisper model")
    args = parser.parse_args()

    openai.api_key = os.environ["OPENAI_ZOOM2TEXT_API_KEY"]

    zooms = get_child_directories(args.pathZoom)
    for dir_with_zoom in zooms:
        print(f'Processing {dir_with_zoom}')
        output_dir = create_directory(dir_with_zoom, args.pathOutput)
        print(f'Created {output_dir}')
        m4a_files = find_m4a_files(dir_with_zoom)
        for m4a_file in m4a_files:
            print(f'Processing {m4a_file}')
            chunk_files = split(dir_with_zoom, m4a_file, output_dir)
            for mp3_file in chunk_files:
                transcript = transcribe(mp3_file)
                save_to_file(mp3_file, transcript)
