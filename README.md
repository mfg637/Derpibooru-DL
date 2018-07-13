# derpibooru.org downloader tool

derpibooru-dl automaticly download and save art in subfolders of download directory.
You can set download directory in `config.py` file (see `config-example.py`)
Change subfolder hierarchy in function `def find_folder(parsed_tags:dict):` at file `derpibooru_dl/tagResponse.py`

## Input
Input must be a link for page with this art. Link must be like this:
```
https://derpibooru.org/1780123
```
or like this:
```
https://derpibooru.org/1777969?q=first_seen_at.gt%3A3+days+ago&sd=desc&sf=score
```
You can get required link by selecting "Copy link address" in thumbnail context menu or from browser url string if art page is opened.

## Run
You can run `derpibooru_dl.py` without any commandline parameters, in this case you can see graphical interface. Add button copy url from clipboard and add it to a listbox. Download button forse downloading. Every minute, if listbox is not empty, all items must be automatically dowloaded.

Also, if program runned with with commadline arguments, program to try to interpreted all arguments like URL of art and then download it. Example of commandline arguments:
```
./derpibooru_dl.py https://derpibooru.org/1777835?q=first_seen_at.gt%3A3+days+ago&sd=desc&sf=score https://derpibooru.org/1780123 https://derpibooru.org/1779010
```

## System Requirements
* Windows or Linux OS
* Python version >= 3.5 with TkInter
* Internet conection