# YT-PhaseDS: A Base Video Dataset for Pretraining Surgical Phase Recognition Models 

This repo is created to download YouTube videos with chapter functionality from selected queries and licence conditions. The chapters in YouTube videos are similar to phases in a surgery and manually created by uploaders, therefore, can be used for pretraining proposed models. 

## Getting Started

1. To install dependencies, we recommend creating a virtual environment:
```
    - python3 -m venv yt-phaseds-env
    - source yt-phaseds-env/bin/activate
    - pip install -r requirements.txt
```
2. Follow the Step 1 in following link to create necessary creditentials and replace existing client secret file: https://developers.google.com/youtube/v3/quickstart/python 


## Usage

The file "queries.py" holds search items. You can update this file according to your language or other requirements. 

Following options can be used for the video search:

```
    -q --query < Single search query to overwrite default search terms >
    -f --filepath < File path where the search result should be stored >
    -n --number < Upperlimit number of videos to search per query >
    -ln --language < Search language, default German >
    -c --creative-common < If specified, searches only Creative Common videos >
    -t --caption < If specified, searches videos with captions > 
    -d --download < If specified, downloads found videos >
    -w --overwrite < If specified, starts search from scratch and overwrites existing results>
```
Run:
```
    - python yt-phaseds *args
```

## License
By downloading and using this code you agree to the terms in the LICENSE. Third-party datasets and software are subject to their respective licenses.
