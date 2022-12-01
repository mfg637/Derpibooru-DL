import pathlib
import re
import argparse

append_id_str = re.compile("Request for download: ([a-z]{2}[0-9]+)")
done_id_str = re.compile("Done downloading: ([a-z]{2}[0-9]+)")
id = re.compile("[a-z]{2}[0-9]+")


def main():
    ids = set()
    downloaded_ids = set()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("log_file", type=pathlib.Path)
    args = arg_parser.parse_args()
    log_file_path: pathlib.Path = args.log_file
    with log_file_path.open("r") as log_file:
        line = log_file.readline().rstrip("\n\r\0")
        while line:
            append_result = append_id_str.search(line)
            done_result = done_id_str.search(line)
            if append_result:
                #ids = append_result.
                ids.add(append_result.group(1))
            elif done_result:
                downloaded_ids.add(done_result.group(1))
            line = log_file.readline().rstrip("\n\r\0")
    lost_ids = ids - downloaded_ids
    for id in lost_ids:
        print(id)


if __name__ == '__main__':
    main()
