from os import path, mkdir
import exifread
import struct
from datetime import datetime

ATOM_HEADER_SIZE = 8
# difference between Unix epoch and QuickTime epoch, in seconds
EPOCH_ADJUSTER = 2082844800


# This function is based on Multimedia Mike's answer in
# https://stackoverflow.com/questions/21355316/getting-metadata-for-mov-video
def get_mov_timestamps(filename):
    creation_time = None

    # search for moov item
    with open(filename, "rb") as f:
        while True:
            atom_header = f.read(ATOM_HEADER_SIZE)
            # ~ print('atom header:', atom_header)  # debug purposes
            if atom_header[4:8] == b'moov':
                break  # found
            else:
                try:
                    atom_size = struct.unpack('>I', atom_header[0:4])[0]
                except struct.error as struct_error:
                    raise RuntimeError(struct_error)

                f.seek(atom_size - 8, 1)

        # found 'moov', look for 'mvhd' and timestamps
        atom_header = f.read(ATOM_HEADER_SIZE)
        if atom_header[4:8] == b'cmov':
            raise RuntimeError('moov atom is compressed')
        elif atom_header[4:8] != b'mvhd':
            raise RuntimeError('expected to find "mvhd" header.')
        else:
            f.seek(4, 1)
            creation_time = struct.unpack('>I', f.read(4))[0] - EPOCH_ADJUSTER
            creation_time = datetime.fromtimestamp(creation_time)
            if creation_time.year < 1990:  # invalid or censored data
                creation_time = None

    return creation_time


def read_timestamp(file):
    with open(file, 'rb') as pic:
        tags = exifread.process_file(pic, stop_tag="EXIF DateTimeOriginal")
        if "EXIF DateTimeOriginal" in tags:
            date_taken = tags["EXIF DateTimeOriginal"]
        else:
            date_taken = get_mov_timestamps(file)

        return date_taken


def get_drive_yearly_folder_ids(drive, root_folder):
    folder_ids = {}
    yearly_folders = \
        drive.ListFile({'q': "'{}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                       .format(root_folder)}).GetList()
    for yearly_folder in yearly_folders:
        folder_ids[yearly_folder['title']] = yearly_folder['id']
    return folder_ids


def get_drive_monthly_folder_ids(drive, yearly_folders):
    folder_ids = {}
    for key, value in yearly_folders.items():
        if key[0].isdigit():
            monthly_folders = \
                drive.ListFile(
                    {'q': "'{}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                    .format(value)}).GetList()
            for monthly_folder in monthly_folders:
                if monthly_folder['title'][0].isdigit():
                    folder_ids[monthly_folder['title']] = monthly_folder['id']
        else:
            print(f'Folder {key} does not start with a digit, ignoring')
    return folder_ids


def remove_prefix(text, prefix):
    return text[len(prefix):] if text.startswith(prefix) else text


def ensure_uploaded_folder_exists(uploaded_folder):
    if not path.exists(uploaded_folder):
        print(f'Creating folder "{uploaded_folder}" for uploaded files')
        mkdir(uploaded_folder)


def create_folder(drive, name, parent_id):
    folder = drive.CreateFile({'title': name,
                             "parents": [{"id": parent_id}],
                             "mimeType": "application/vnd.google-apps.folder"})
    folder.Upload()
    print(f'Created folder {name} to Drive')
    return folder['id']


def create_drive_folder(folder_name, yearly_folders, root_folder, drive):
    split_folder_id = folder_name.split('/')
    folder_year = split_folder_id[0]

    if folder_year in yearly_folders:
        return create_folder(drive, folder_name, yearly_folders[folder_year])
    else:
        yearly_folder_id = create_folder(drive, folder_year, root_folder)
        return create_folder(drive, folder_name, yearly_folder_id)
