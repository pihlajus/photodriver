from os import listdir, rename
from os.path import isfile, join
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from helper_functions import *


def main():
    DRIVE_ROOT_FOLDER = '<your_drive_root_folder_id>'
    PHOTO_FOLDER = '<your_photo_folder>'


    # Login to Google Drive and create drive object
    g_login = GoogleAuth()
    g_login.LocalWebserverAuth()
    drive = GoogleDrive(g_login)

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
                timestamp = str(read_timestamp(file_full_path))

                parsed_date = remove_prefix(timestamp, "Date ").replace('-', ':')
                datetime_date = datetime.strptime(parsed_date, '%Y:%m:%d %H:%M:%S')
                drive_folder_date = datetime_date.strftime('%Y/%-m')

                upload_folder_id = None
                for key, value in monthly_folder_ids.items():
                    if key == drive_folder_date:
                        upload_folder_id = value
                        break
                if upload_folder_id is None:
                    print(f'Folder {drive_folder_date} not found or not yet created')
                    upload_folder_id = create_drive_folder(drive_folder_date, yearly_folder_ids, DRIVE_ROOT_FOLDER, drive)
                    monthly_folder_ids[drive_folder_date] = upload_folder_id

                drive_file = drive.CreateFile({'parents': [{'id': upload_folder_id}]})
                drive_file.SetContentFile(file_full_path)
                drive_file['title'] = datetime_date.strftime('%Y.%m.%d_%H:%M:%S')
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

