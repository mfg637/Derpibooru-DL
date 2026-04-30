# Derpibooru-DL

Downloads media content from multiple booru-like sites.

## Supported sites

- derpibooru.org
- tantabus.ai
- ponybooru.org
- twibooru.org
- e621.net
- furbooru.org

## Core features

- configurable saving path and name format
- download server and userscript to add download button directly to the site page
- interactive shell for downloading with CLI and config file editing
- optional integration with medialib service

## Executable files

### main tools

- `derpibooru_dl.py` - the main downloader. Runs in console mode by default,
  or GUI mode if "enable gui" . Can download bunch of URLs or IDs with
  `--append` argument Has a minimal system requirements
  in simple downloading mode:
  - Linux or Windows
  - Python version >= 3.12
  - TkInter for GUI mode
  - Internet conection

- `interactive_config_generator.py` — interactive editor of `config.json`.
  Allows to set up parameters in groups:
  - server
  - filesystem
  - `api_keys`
  - ui
  - database
  - medialib

Alternately, setting with environment parameters supported.
Look at `config/__init__.py`

### Automation & Bulk Loading

- `philomena_bulk_loader.py` — bulk downloading by search query. Supporting sites:
  - derpibooru.org
  - tantabus.ai
  - ponybooru.org
  - furbooru.org
- `create_album_e621.py` — creates album in medialib service by e621 pool ID

### Service Integration

- `derpibooru_dl_userscript_server` — Local http server for accepting
  requests from userscript (placed in `static/js/derpibooru_dl_client_script.js`
- `import_content.py` — import already existing files into medialib service.
- `reprocess_from_ids.py` — extracting ID from file names and redownloads it.

Scripts `import_content.py`, `reprocess_from_ids.py`, and `create_album_e621.py`
require not None `ml_host` and `ml_port`.

## Install and set up

1. Clone repository
2. Install dependency (preferred in virtual environment): `pip install -r python-dependencies.txt`
3. Set up configuration
   `python interactive_config_generator.py`

Use `set_group` command to make group current and `set_option <option_name>`
to set option value.

