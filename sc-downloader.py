from __future__ import division
import os
import re
import unicodedata
import sys

import requests
#import argh
import humanize
import getopt

class SoundCloudClient(object):

    def __init__(self, client_id):
        self.client_id = client_id

    def request(self, action, **params):
        params['client_id'] = self.client_id
        stream = params.pop('stream') if 'stream' in params else False

        if 'http' not in action:
            url = 'https://api.soundcloud.com/' + action + '.json'
        else:
            url = action
        
        # EXEs packages with PyInstaller has a problem finding cacerts.txt. One way to avoid this 
        # is to use verify=False
        return requests.get(url, verify=False, stream=stream, params=params)


def normalize(filename):
    '''Normalize the given name to make it a valid filename'''
    if isinstance(filename, unicode):
        filename = unicodedata.normalize('NFKD', filename)

    return re.sub(r'[\/\\\:\*\?\"\<\>\|]', '', filename)

def download_track(client, track, output_dir):
    title = normalize(track['title']) + '.' + track['original_format']
    audio_track = os.path.join(output_dir, title)

    if os.path.exists(audio_track):
        #print u'Track {} already exists'.format(track['id'])
        print u'Track {} already exists'.format(title)
        return

    stream_url = track['stream_url']
    request = client.request(stream_url, stream=True)
    downloaded_track = u'{}.part'.format(audio_track)
    bytes_downloaded = os.stat(downloaded_track).st_size if os.path.exists(downloaded_track) else 0
    content_length = int(request.headers['content-length']) + bytes_downloaded

    CHUNK_SIZE = 100 * 1024
    time_before = time.time()
    with open(downloaded_track, 'wb') as f:
        for i, chunk in enumerate(request.iter_content(CHUNK_SIZE)):
            f.write(chunk)
            f.flush()

            # Calculate download speed
            now = time.time()
            try:
                download_speed = (CHUNK_SIZE)  / (now - time_before)
            except ZeroDivisionError:
                pass
            time_before = now

            if i % 2 == 0: # Print progress after
                # \r used to return the cursor to beginning of line, so I can write progress on a single line.
                # The comma at the end of line is important, to stop the 'print' command from printing an additional new line
                print u'\rDownloading track {}, {:.1f}%, {}/s   '.format(
                                                                            title,
                                                                            f.tell() * 100 / content_length, 
                                                                            humanize.naturalsize(download_speed)),

    os.rename(downloaded_track, audio_track)

def add_subscription(url):
    try:
        f = open("subscriptions.txt", "w")
        subs = f.read().split("\n")
        if (url in subs):
            print "You already have a subscription for this playlist"
        else:
            f.write(url+"\n")
    except IOError:
        print "Can't save the subscription"
    f.close()
    

def update_subscriptions():
    try:
        f = open("subscriptions.txt", "r")
        subs = f.read().split("\n")
    except IOError:
        print "Error fetching subscriptinos file..."
    return subs[:-1]

'''Download the given track/playlist'''
def do_Download(url, client_id, output_dir, isUpdate):
    client = SoundCloudClient(client_id)
    print 'Reading URL...'
    response = client.request('resolve', url=url).json()
    
    if 'errors' in response:
        print "Error {} on the URL".format(response['errors'][0]['error_message'])
        return
    if 'plan' in response:
        print "Sorry, you need a SoundCloud subscription to download this"
        return

    if 'tracks' in response: # a playlist
        print 'Playlist has {} tracks'.format(response['track_count'])
        
        title = response['title']
        title = normalize(title)
        
        output_dir = os.path.join(output_dir, title)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for track in response['tracks']:
            download_track(client, track, output_dir=output_dir)
        
        if not isUpdate:
            subscription = raw_input('Do you want to subscribe to this playlist Y/N ?')
            if subscription.upper() == 'Y':
                add_subscription(url)

    else:
        download_track(client, response, output_dir=output_dir)

def main(argv):
    try:
      opts, args = getopt.getopt(argv,"hud:o:c:",["download=", "output_dir=", "client_id="])
    except getopt.GetoptError:
      sys.exit()

    url = ''
    output_dir='.'
    client_id = 'b45b1aa10f1ac2941910a7f0d10f8e28'
    update = False
    for opt, arg in opts:
        if opt == '-h':
            print 'sc-downloader.py [-d <trakURL>] [-o <output_directory>] [-c <client_id>] [-u]'
            sys.exit()
        elif opt in ("-d", "--download"):
            url = arg
        elif opt in ("-o", "--output_dir"):
            output_dir = arg
        elif opt in ("-c", "--client_id"):
            client_id = arg
        elif opt == '-u':
            update = True #Just update subscriptions

    if update:
        links = update_subscriptions()
        for l in links: #request download for every subscription
            do_Download(l, client_id, output_dir, update)
    elif url != '':
            do_Download(url, client_id, output_dir, update)


if __name__ == '__main__':
    main(sys.argv[1:])
