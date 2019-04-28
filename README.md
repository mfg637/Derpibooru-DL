# derpibooru.org downloader tool

derpibooru-dl automaticly download and save art in subfolders of download directory.
You can set download directory in `config.py` file (see `config-example.py`)
Change subfolder hierarchy in function `def find_folder(parsed_tags:dict):` at file `derpibooru_dl/tagResponse.py`

## Executable files
* `derpibooru_dl.py` - a simple downloader. Can be run in console or GUI mode. Has a minimal system requirements in simple downloading mode:
    * Windows or Linux OS
    * Python version >= 3.5 with TkInter
    * Internet conection
* `autodownload_my_upvotes.py` - download new images from your upvotes collection. <b>Your API key required - set `key` string in file `config.py`.</b> It's a console script. 
* `browser_main.py` - Browser. Show thumbnails in grid and checkbox up for every thumbnail. When you get another page - application add checked images to download queue. Search by tags supported.
Addiional to minimal system requirements on `derpibooru_dl.py`, this application required [FFmpeg](http://ffmpeg.org/) and [Pillow (PIL fork)](https://pypi.org/project/Pillow/)
 
 Faving and upvoting not supported.

## Run applicatons
### Run `derpibooru-dl.py`

You can run `derpibooru_dl.py` without any commandline parameters, in this case you can see graphical interface. Add button copy url from clipboard and add it to a listbox. Download button force downloading. By default, downloading starts if you add item in empty list, and continue, until list is not empty.

Also, if program runs with with commandline arguments, program to try to interpreted all arguments like URL of art and then download it. Example of commandline arguments:
```
./derpibooru_dl.py https://derpibooru.org/1777835?q=first_seen_at.gt%3A3+days+ago&sd=desc&sf=score https://derpibooru.org/1780123 https://derpibooru.org/1779010
```

## Input for `derpibooru_dl.py`
Input must be a link for page with this art. Link must be like this:
```
https://derpibooru.org/1780123
```
or like this:
```
https://derpibooru.org/1777969?q=first_seen_at.gt%3A3+days+ago&sd=desc&sf=score
```
You can get required link by selecting "Copy link address" in thumbnail context menu or from browser url string if art page is opened.

### Run `autodownload_my_upvotes.py`

```
./autodownload_my_upvotes.py [int PERIOD_LEN=3 [string PERIOD_NAME=days]]
```

All parameters are optional. By default it will download images, posted by 3 days age and newer.

Possible values for `PERIOD_LEN` is positive integer numbers.

Possible values for `PERIOD_NAME`:
* `days`
* `months`
* `years`

### Run `browser_main.py`

Exists only one way to do this:

```
./browser_main.py
```
on Linux or

```
browser_main.py
```
on Windows.