import logging
import boto3
import os
from datetime import datetime
import math

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load env
LOCAL_STORAGE_DIR = '/tmp/pieces'
FILE_LIST = '/tmp/records.txt'
S3_BUCKET = os.getenv('S3_BUCKET')
S3_SOURCE_PREFIX = 'pieces'
S3_DEST_PREFIX = 'backup'
TIME_RANGE = int(os.getenv('TIME_RANGE', '7200'))

s3_resource = boto3.resource('s3')
bucket = s3_resource.Bucket(S3_BUCKET)


def lambda_handler(event, context):
    # Calculate time mark
    time_mark = (math.ceil(datetime.now().timestamp() / TIME_RANGE) * TIME_RANGE) - TIME_RANGE

    # Create dir for storing video pieces
    os.system(f'mkdir {LOCAL_STORAGE_DIR}')

    download_video_pieces(time_mark)
    files = os.listdir(LOCAL_STORAGE_DIR)
    # Sort by datetime in file name
    files.sort(key=sort_by_file_name)

    with open(FILE_LIST, 'w+') as records:
        for file in files:
            records.write(f'file {LOCAL_STORAGE_DIR}/{file}\n')

    with open(FILE_LIST) as records:
        for line in records:
            logger.info(line)

    os.system(f'ffmpeg -f concat -safe 0 -i {FILE_LIST} -c copy /tmp/{time_mark}.mkv')

    bucket.upload_file(f'/tmp/{time_mark}.mkv', f'{S3_DEST_PREFIX}/{time_mark}.mkv', ExtraArgs={'ContentType': 'video/x-matroska'})


def download_video_pieces(time_mark: int):
    keys = []

    s3_files = bucket.objects.filter(
        Prefix=f'{S3_SOURCE_PREFIX}/{time_mark}',
    )
    for file in s3_files:
        # Only mkv file
        if os.path.splitext(file.key)[1] == '.mkv':
            keys.append(file.key)

    logger.info('file need to download: ')
    logger.info(keys)

    for key in keys:
        file_name = key.split('/')[-1]
        bucket.download_file(key, f'{LOCAL_STORAGE_DIR}/{file_name}')


def sort_by_file_name(name):
    time_string = name.split('/')[-1].split('.')[0]
    time = datetime.strptime(time_string, "%Y%m%dT%H%M%S")
    ts = datetime.timestamp(time)
    return ts
