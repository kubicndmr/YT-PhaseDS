# Adapted from the quickstart example at https://developers.google.com/youtube/v3/quickstart/python
from __future__ import unicode_literals

import os
import json
import asyncio
import queries
import argparse
import youtube_dl
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from youtubesearchpython.__future__ import Video, VideosSearch

# Set up argument parsing
parser = argparse.ArgumentParser(description = 
    'Search and download videos with chapter function for given queries')
parser.add_argument('-q','--query', type = str,
        help = 'Single search query to overwrite default search terms',
        default = 'None', dest = 'query')
parser.add_argument('-f','--filepath', type = str,
        help = 'File path where the search result should be stored.',
        default= 'data/', dest = 'filepath')
parser.add_argument('-n', '--number', type = int, 
        help = 'Number of videos to search per query', 
        default = 20, dest = 'number')
parser.add_argument('-ln','--language', type = str,
        help = 'Search language, default german',
        default = 'de', dest = 'language')
parser.add_argument('-c', '--creative-common', action='store_true',
        help = 'If specified, searches only Creative Common videos', 
        dest = 'license')
parser.add_argument('-t', '--caption', action='store_true',
        help = 'If specified, searches videos with captions', 
        dest = 'caption')
parser.add_argument('-d', '--download', action='store_true',
        help = 'If specified, downloads found videos', 
        dest = 'download')
parser.add_argument('-w', '--overwrite', action='store_true',
        help = 'If specified, starts search from scratch and overwrites existing results', 
        dest = 'overwrite')

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. Requires an application to be registered with the Youtube Data API: 
# https://developers.google.com/youtube/v3/quickstart/python
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

def get_authenticated_service():
    """
    Performs authentication by providing the client_secret.json API information, 
    prompts user to authenticate via their Google account
    """
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    try:
        credentials = Credentials.from_authorized_user_file('tokens/credentials.json', scopes=SCOPES)
    except:
        credentials = flow.run_console()
    credentials_dict = {
	    'token': credentials.token,
	    'refresh_token': credentials.refresh_token,
	    'id_token': credentials.id_token,
	    'token_uri': credentials.token_uri,
	    'client_id': credentials.client_id,
	    'client_secret': credentials.client_secret
    }
    with open('tokens/credentials.json', 'w') as cred_file:
        json.dump(credentials_dict, cred_file)
    return build(API_SERVICE_NAME, API_VERSION, credentials = credentials)


def get_chapters(description):
    '''
    How chapters are created: 
        https://www.youtube.com/watch?v=b1Fo_M_tj6w&t=79s
    
    Youtube Chapter format in description:
        <num><:><num><space><title> / <num><:><num><:><num><space><title> or 
        <title><space><num><:><num> / <title><space><num><:><num><:><num>

    Output:
        chapers(list) holds chapter beginning time stamps.
    
        Format:
            ['<num><:><num>', '<num><:><num>', ...]
    '''
    chapters = list()
    lines = description.split('\n')

    for line in lines:
        line = line.strip() #remove leading and tailing spaces
        line_space = line.split(' ')
        line_backward = ' '.join(line_space[::-1])
        for sub_line in [line, line_backward]:
            line_column = sub_line.split(':')
            if len(line_column) == 2: # <num><:><num>
                if line_column[0].isnumeric():             
                    line_space = line_column[1].split(' ')
                    if line_space[0].isnumeric():
                        chapters.append(line_column[0] + ':' + line_space[0])
            if len(line_column) == 3: # <num><:><num><:><num>
                if line_column[0].isnumeric() and line_column[1].isnumeric():             
                    line_space = line_column[2].split(' ')
                    if line_space[0].isnumeric():
                        chapters.append(line_column[0] + ':' + line_column[1] + ':' + line_space[0])
    
    if len(chapters) < 3: # eliminate if few chapters exists
        chapters = list()

    return chapters


def isCC(service, video_id):
    '''
    Checks if the video has a Creative Common Licence.

    Returns bool
    '''
    request = service.videos().list(part='status',
                id=video_id)
    
    response = request.execute()['items'][0]['status']

    return response['license'] == 'creativeCommon'


def isCaption(video_id, language):
    '''
    Checks if the video has a Caption in given language.

    Returns bool
    '''
    caption_check = False

    ydl_opts = {
        'skip_download': True,
        'logger': MyLogger()}
    
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(video_id, download = False)

        if (language in video_info['subtitles'].keys() or 
            language in video_info['automatic_captions'].keys()):
            caption_check = True
    except:
        caption_check = False

    return  caption_check 


async def get_videoList(service, query, number_videos, 
        language, license_flag, caption_flag, patience = 5):
    '''
    Returns list of videos and time stamps for given query 
    if they include chapter information.

    service: youtube class
        output of  the get_authenticated_service

    query:              string
        single search term

    number_videos:      int
        target number of videos to search
        
    language:           str
        youtube search language

    license_flag:       bool
        if true, searches only creative common videos

    caption_flag:    bool
        if true, searches only videos with captions

    patience:       int
        number of youtube pages to search until reaching
        number_videos

    Output:         list
        [[<title>, <id>, <duration>, <chapters(list)>], ...]
    '''
    chaptered_videos = list()

    page_count = 0
    video_count = 0
    
    videosSearch = VideosSearch(query, language = language)

    while page_count < patience and video_count < number_videos:
        video_results = await videosSearch.next()
        video_results = video_results['result']
        
        for video_result in video_results:
            video_title = video_result['title']
            video_info = await Video.getInfo(video_result['id'])

            chapters = get_chapters(video_info['description'])
        
            if chapters:
                if license_flag:
                    license_check = isCC(service, video_result['id'])
                else:
                    license_check = False
                
                if caption_flag:
                    caption_check = isCaption(video_result['id'], language)
                else:
                    caption_check = False
                
                if license_flag == license_check and caption_flag == caption_check:
                    chaptered_videos.append([video_title, video_result['link'], 
                        video_result['duration'], chapters])
                    video_count += 1

        page_count += 1

    return chaptered_videos[:number_videos]


if __name__ == '__main__':
    # Parse arguments
    args = vars(parser.parse_args())
    
    search_queries = [args['query']]
    
    if search_queries == ['None']:
        search_queries = queries.first_queries
        args['query'] = search_queries
    
    write_path = args['filepath']
    if not os.path.exists(write_path):
        os.makedirs(write_path)

    number_videos = args['number']
    
    language = args['language']

    license_flag = args['license']
    
    caption_flag = args['caption']

    download_flag = args['download']

    overwrite_flag = args['overwrite']

    # Authenticate with the API
    service = get_authenticated_service()

    # Check previous searches
    if (os.path.exists(write_path + 'results.json') and 
        overwrite_flag == False):
        
        with open(write_path + 'results.json', 'rb') as f:
            video_list = json.load(f)

    else:
        # Log search settings
        with open(write_path + 'logs.json', 'w') as f:
            json.dump(args, f, indent = 2)

        video_list = list()
        # Search
        for query in search_queries:
            search_result = asyncio.run(get_videoList(service, query, 
                number_videos, language, license_flag, caption_flag))

            print('For query "{}", "{}" videos are found.'.format(query, len(search_result)))

            for s in search_result:
                video_list.append(s)

        print('Total {} videos are found.'.format(len(video_list)))

        with open(write_path + 'results.json', 'w') as f:
            json.dump(video_list, f, indent = 2)
    
    # Download
    if download_flag:
        with open(write_path + 'results.json', 'rb') as f:
            video_list = json.load(f)
        
        for video in video_list:
            print('Downloading... {}'.format(video[0]))
 
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitle': '--write-sub',
                'subtitleslangs': [language],
                'subtitlesformat': "best",
                'nooverwrites': True,
                'format': 'mp4',
                'outtmpl': "{}%(id)s".format(write_path),
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video[1]])