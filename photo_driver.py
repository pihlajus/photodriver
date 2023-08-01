from os import listdir, rename
from os.path import isfile, join
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from exif_utils import *
from google_drive_utils import *

DRIVE_ROOT_FOLDER = '<your_drive_root_folder_id>'
PHOTO_FOLDER = '<your_photo_folder>'


def main():
    # Login to Google Drive and create drive object
    g_login = GoogleAuth()
    g_login.LocalWebserverAuth()
    drive = GoogleDrive(g_login)

    # Get existing folders
    yearly_folder_ids = get_drive_yearly_folder_ids(drive, DRIVE_ROOT_FOLDER)
    monthly_folder_ids = get_drive_monthly_folder_ids(drive, yearly_folder_ids)

    uploaded_folder = PHOTO_FOLDER + '/uploaded'
    ensure_uploaded_folder_exists(uploaded_folder)

    file_list = [f for f in listdir(PHOTO_FOLDER) if isfile(join(PHOTO_FOLDER, f))]

    uploaded = 0
    upload_failed = 0

    for file_name in file_list:
        if file_name != '.DS_Store':
            file_full_path = PHOTO_FOLDER + '/' + file_name
            try:
                datetime_date, drive_folder_date = get_timestamps(file_full_path)

                upload_folder_id, monthly_folder_ids = get_or_create_folder_id(DRIVE_ROOT_FOLDER, drive,
                                                                               drive_folder_date, monthly_folder_ids,
                                                                               yearly_folder_ids)

                drive_file = drive.CreateFile({'parents': [{'id': upload_folder_id}]})
                drive_file.SetContentFile(file_full_path)

                coordinates = get_location(file_full_path)
                location = get_area_from_location(coordinates) if coordinates is not None else None

                drive_file['title'] = datetime_date.strftime('%Y.%m.%d_%H:%M:%S') + ('_' + location if location else '')

                drive_file.Upload()
                rename(file_full_path, uploaded_folder + '/' + file_name)
                uploaded += 1
                print(f'{file_name} uploaded to folder {drive_folder_date}')
            except RuntimeError as error:
                print(f'Cannot handle file {file_name}: "{error}". Skipping to next...')
                upload_failed += 1

    print(f'Uploaded {uploaded} photos, {upload_failed} uploads failed')


if __name__ == "__main__":
    main()
