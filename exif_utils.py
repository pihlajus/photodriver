from os import path
import exifread
import struct
import subprocess
from datetime import datetime
from geopy.geocoders import Nominatim
from GPSPhoto import gpsphoto

ATOM_HEADER_SIZE = 8
# difference between Unix epoch and QuickTime epoch, in seconds
EPOCH_ADJUSTER = 2082844800


# This function is based on Multimedia Mike's answer in
# https://stackoverflow.com/questions/21355316/getting-metadata-for-mov-video
def get_video_timestamp(file):
    creation_time = None

    # search for moov item
    with open(file, "rb") as f:
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


def is_video(file):
    file_extension = path.splitext(file)[1][1:]
    return file_extension.lower() != "jpeg"


def get_photo_timestamp(file):
    with open(file, 'rb') as pic:
        tags = exifread.process_file(pic)
        return tags["EXIF DateTimeOriginal"]


def get_timestamp(file):
    return get_video_timestamp(file) if is_video(file) else get_photo_timestamp(file)


def get_timestamps(file_full_path):
    timestamp = str(get_timestamp(file_full_path))
    parsed_date = remove_prefix(timestamp, "Date ").replace('-', ':')
    datetime_date = datetime.strptime(parsed_date, '%Y:%m:%d %H:%M:%S')
    drive_folder_date = datetime_date.strftime('%Y/%-m')
    return datetime_date, drive_folder_date


# Some rough rules (found by trial and error) for parsing sensible location
def get_area_from_location(input_string):
    parts = input_string.split(', ')
    if parts[0].isdigit():
        return parts[2]
    elif parts[1][0].isdigit():
        return parts[0]
    else:
        return parts[1]


def get_video_location(video_path):
    try:
        output = subprocess.check_output([
            'exiftool',
            '-GPSLatitude',
            '-GPSLongitude',
            '-n',
            '-T',
            '-c', '%.6f',
            video_path
        ]).decode().strip().split('\t')

        if len(output) == 2:
            latitude = float(output[0])
            longitude = float(output[1])
            # return latitude, longitude
            geo_locator = Nominatim(user_agent="GetLoc")
            # Combine latitude and longitude into a single string
            location_str = f"{latitude}, {longitude}"

            # Use reverse geocoding to get the location based on latitude and longitude
            location = geo_locator.reverse(location_str)

            # Extract the address from the location object
            address = location.address if location else None

            return address

    except subprocess.CalledProcessError:
        pass

    # Return None if location extraction fails
    return None


def get_photo_location(file):
    gps_data = gpsphoto.getGPSData(file)
    if len(gps_data) == 0:
        print(f'No location data found from {file}')
        return None
    loc_string = str(gps_data.get("Latitude")) + ", " + str(gps_data.get("Longitude"))
    geo_location = Nominatim(user_agent="GetLoc")
    location = geo_location.reverse(loc_string).address
    return location


def get_location(file):
    return get_video_location(file) if is_video(file) else get_photo_location(file)


def remove_prefix(text, prefix):
    return text[len(prefix):] if text.startswith(prefix) else text
