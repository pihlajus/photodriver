from os import path, mkdir


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
            print(f'Folder "{key}" does not start with a digit, ignoring')
    return folder_ids


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


def get_monthly_folder_id(ids, folder_date):
    for key, value in ids.items():
        if key == folder_date:
            return value
    return None


def get_or_create_folder_id(root_folder, drive, drive_folder_date, monthly_folder_ids, yearly_folder_ids):
    upload_folder_id = get_monthly_folder_id(monthly_folder_ids, drive_folder_date)
    if upload_folder_id is None:
        print(f'Folder {drive_folder_date} not found, creating it...')
        upload_folder_id = create_drive_folder(drive_folder_date, yearly_folder_ids, root_folder,
                                               drive)
        monthly_folder_ids[drive_folder_date] = upload_folder_id

    return upload_folder_id, monthly_folder_ids
