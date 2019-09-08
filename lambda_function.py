import time
import boto3
from botocore.vendored import requests
import json
import re

def lambda_handler(event, context):
    uri = event['uri']
    return transcribeAudio(uri)

# takes in the url string of the file for transcribe
# the bucket needs to be the same region as the end user
def transcribeAudio(uri):
    transcribe = boto3.client('transcribe')

    suffix = str(int(round(time.time() * 1000)))
    job_name = "TranscribeJob_" + suffix

    media = uri.split(".")[-1]

    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': uri},
        MediaFormat='mp4',
        LanguageCode='en-US'
    )

    # constantly gets response with a one-sec delay
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        time.sleep(0.1)

    # A presigned URL is generated by an AWS user who has access to the object.

    # The presigned URL remains valid for a limited period of time after URL
    # is generated.
    response_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']

    if response_uri is not None:
        response = requests.get(response_uri)

    text = response.json()['results']['transcripts']
    schedule = response.json()['results']['items']
    final_text = text[0]['transcript']

    # divides text into sections by punctuations
    sections = re.split(';|,|\.|\*|\n', final_text)
    sections = list(filter(lambda x: x != "", sections))

    # computes how many words are there in each section
    lengths = [len(section.split()) for section in sections]
    valid_lengths = list(filter(lambda x: x != 0, lengths))

    # takes in account the accumulated section breaks and weights
    fix = list(range(0, len(valid_lengths)))
    weight = [0]
    acc = 0
    for num in range(0, len(valid_lengths) -1):
        acc += valid_lengths[num]
        weight.append(acc)

    lis = [valid_lengths, fix, weight]
    positions = [sum(x) - 1 for x in zip(*lis)]
    puncs = [schedule[pos] for pos in positions]

    # finds the end_time for each section, and inserts a head for the beginning
    # of the audio
    endstamps = [float(punc['end_time']) for punc in puncs]
    endstamps.insert(0, 0.00)
    endstamps = endstamps[0:-1]

    # constructs a timeline with each section labelled its start time and end
    # time
    timeline = dict()

    for index in range(len(sections)):
        timeline[endstamps[index]] = sections[index]

    return json.dumps(timeline)

# sample output json format:
#  section  [start_time, end_time]
# {"this": ["0.00", "0.55"],
#  " It was a bright Cartier in April": ["0.55", "3.26"],
#  " and the clocks were striking": ["3.26", "4.73"],
#  " 13 Winston Smith he string": ["4.73", "7.72"],
#  " nestled into he expressed in an effort to escape the vile winged slipped quickly through the glass": ["7.72", "13.54"],
#  " Doors of Victory mentions Doe not quickly enough to prevent this world gritty dust from entering along with him": ["13.54", "20.7"],
#  " The hallway smells off boiled cabbage and old rug mats": ["20.7", "28.5"],
#  " At one end of it is a colored posters too large for England": ["28.5", "32.77"],
#  " Display had been tackled did wall": ["32.77", "35.36"]}

