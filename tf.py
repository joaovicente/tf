import argparse
import os
import subprocess
import logging
import textwrap
from exiftool import ExifToolHelper


def ffmpeg_log_level(log_level: str):
    # from https://ffmpeg.org/ffmpeg.html
    log_level_map = {
        'DEBUG': "32",
        'INFO': "24",  # ffmpeg is too verbose - use -l DEBUG instead
        'WARNING': "24",
        'ERROR': "16"
    }
    return log_level_map[log_level]


def transform_video(input_file: str, dry_run: bool, force: bool, erase: bool, log_level: str):
    """
    Converts a file to mp4. Requires ffmpeg and libx264
    input_file -- The file to convert
    dry_run -- Whether to actually convert the file
    """
    output_file = ".".join(input_file.split('.')[:-1]) + '.MP4'
    ffmpeg_command = f'ffmpeg -loglevel {ffmpeg_log_level(log_level)} -i "{input_file}" -b:a 32k "{output_file}"'

    if not dry_run:
        logging.info(f'Transforming "{input_file}" to "{output_file}"')
    else:
        logging.info(f'Simulating transformation of "{input_file}" to "{output_file}"')
    if not os.path.exists(input_file):
        logging.error(f'"{input_file}" does not exist')
        return
    else:
        datetags = {}
        with ExifToolHelper() as et:
            metadata = et.get_metadata(input_file)[0]
            datetags = {key: metadata[key] for key in metadata if 'Date' in key}
            logging.debug(f'Detected date tags in "{input_file}": {datetags}')
    if os.path.exists(output_file):
        if force:
            logging.info(f'"{output_file}" already exists. deleting before transformation.')
            os.remove(output_file)
        else:
            if erase:
                logging.warning(f'"{input_file}" already transformed. Deleting.')
                os.remove(input_file)
            else:
                logging.warning(f'"{output_file}" already exists. Skipping transformation.')
            return
    # Transform video now
    if not dry_run:
        # ffmpeg
        subprocess.call(ffmpeg_command, shell=True)
        # Insert tags
        ExifToolHelper().set_tags(files=output_file, tags=datetags)
        # exiftool renames original file appending _original to it (e.g. myvideo.MP4_original)
        exiftool_renamed_file = output_file + '_original'
        logging.debug(f'Removing exiftool renamed file "{exiftool_renamed_file}"')
        if os.path.exists(exiftool_renamed_file):
            os.remove(exiftool_renamed_file)
        logging.info(f'"{output_file}" created')


def supported_input_format(input_file):
    allowed_extensions = ('MKV', 'AVI', 'MPG', 'WMV', 'MOV', 'M4V', '3GP', 'MPEG', 'MPE', 'OGM', 'FLV', 'DIVX', 'VOB',
                          'QT')
    return input_file.split('.')[-1].upper() in allowed_extensions


def dispatch_transformation(input_file_list, dryrun, force, erase, log_level):
    for file in input_file_list:
        if supported_input_format(file):
            transform_video(file, dryrun, force, erase, log_level)


def main(output_format, dryrun, force, log_level, recursive, erase, input_files=None):
    logging.debug(f'Input file: "{input_files}"')
    logging.debug(f'Output format: {output_format}')
    logging.debug(f'Dry run: {dryrun}')
    logging.debug(f'Log level: {log_level}')
    logging.debug(f'Force transformation: {force}')
    logging.debug(f'Recursive: {recursive}')
    recursive_file_list = []
    if recursive:
        # validate supplied path is a directory
        if len(input_files) != 1:
            logging.error(f'Only one path supported. Supplied "{input_files}"')
        else:
            root_path = input_files[0]
            if not os.path.isdir(root_path):
                logging.error(f'Path supplied is not a directory: "{root_path}"')
            else:
                logging.info(f'Transforming files recursively from root directory: "{root_path}"')
                for root, dirs, files in os.walk(root_path):
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        recursive_file_list.append(file_path)
                dispatch_transformation(recursive_file_list, dryrun, force, erase, log_level)
    else:
        dispatch_transformation(input_files, dryrun, force, erase, log_level)


class RawFormatter(argparse.HelpFormatter):
    def _fill_text(self, text, width, indent):
        return "\n".join(
            [textwrap.fill(line, width) for line in textwrap.indent(textwrap.dedent(text), indent).splitlines()])


description = "Transform videos to MP4 format"
usage = '''
    ## Pre-requirement:
    Build and install exiftool as per https://exiftool.org/install.html#Unix

    ## Usage examples:
    # Transform single video to MP4
    $ python tf.py myvideo.3GP

    # Transform all videos in a given folder to MP4 (-f to force transformation)
    # current folder
    $ python tf.py *
    specific folder
    $ python tf.py any-file-under-this-folder/*

    # Transform all videos from a folder and children to MP4
    $ python tf.py -r /path/to/media
'''
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=description,
        epilog=usage,
        formatter_class=RawFormatter)
    parser.add_argument("input_files", nargs="+", help="Files to transform")
    parser.add_argument("-d", "--dryrun", action="store_true", help="Perform a dry run (skip transformation)")
    parser.add_argument("-f", "--force", action="store_true", help="Force transformation even if output file exists")
    parser.add_argument("-l", "--log-level", help="Log level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        default="INFO")
    parser.add_argument("-o", "--output-format",  help="Output format", required=False)
    parser.add_argument("-r", "--recursive", action="store_true", help="Transform files in sub folders")
    parser.add_argument("-e", "--erase", action="store_true",
                        help="Erase original if tranformation was previously successful")
    args = parser.parse_args()
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging._nameToLevel[args.log_level])
    main(args.output_format, args.dryrun, args.force, args.log_level, args.recursive, args.erase, args.input_files)
