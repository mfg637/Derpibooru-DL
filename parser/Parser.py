import config
import urllib.request
import urllib.parse
import threading
import multiprocessing
import abc
import requests

if config.enable_images_optimisations:
    from derpibooru_dl import imgOptimizer


downloader_thread = threading.Thread()
download_queue = []


class Parser(abc.ABC):
    def __init__(self, url, parsed_data=None):
        self._url = url
        self._parsed_data = parsed_data

    @staticmethod
    def get_id_by_url(URL: str):
        return URL.split('?')[0].split('/')[-1]

    def append2queue(self, **kwargs):
        global downloader_thread
        global download_queue
        download_queue.append(kwargs)
        if not downloader_thread.is_alive():
            downloader_thread = threading.Thread(target=self.async_downloader)
            downloader_thread.start()

    def async_downloader(self):
        global download_queue
        while len(download_queue):
            print("Queue: lost {} images".format(len(download_queue)))
            current_download = download_queue.pop()
            pipe=multiprocessing.Pipe()
            params = current_download
            params['pipe'] = pipe[1]
            process = multiprocessing.Process(target=self.save_image, kwargs=params)
            process.start()
            imgOptimizer.sumos, imgOptimizer.sumsize, imgOptimizer.avq, imgOptimizer.items = pipe[0].recv()
            process.join()
            print("Queue: lost {} images".format(len(download_queue)))

    @staticmethod
    def download_file(filename: str, src_url: str) -> None:
        request_data = requests.get(src_url)
        file = open(filename, 'wb')
        file.write(request_data.content)
        file.close()

    def in_memory_transcode(self, src_url, name, tags, output_directory, pipe):
        source = self.do_binary_request(src_url)
        transcoder = imgOptimizer.get_memory_transcoder(
            source, output_directory, name, tags, pipe
        )
        transcoder.transcode()

    @staticmethod
    def do_binary_request(url):
        request_data = requests.get(url)
        source = bytearray(request_data.content)
        return source

    @abc.abstractmethod
    def save_image(self, output_directory: str, data: dict, tags: dict = None, pipe = None):
        pass

    @abc.abstractmethod
    def parseJSON(self, _type="images"):
        pass

    @abc.abstractmethod
    def tagIndex(self):
        pass
