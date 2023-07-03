import os
import argparse


def get_child_directories(directory_path):
    try:
        return [name for name in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, name))]
    except FileNotFoundError:
        return "The provided directory does not exist."
    except NotADirectoryError:
        return "The provided path is not a directory."
    except PermissionError:
        return "Permission denied for the provided directory."


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List child directories of a given directory")
    parser.add_argument("-p", "--path", type=str, help="The path to the directory")
    args = parser.parse_args()

    print(get_child_directories(args.path))
