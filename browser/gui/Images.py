#!/usr/bin/python3
# -*- coding: utf-8 -*- 
import tkinter
from .. import net
import PIL.Image
import PIL.ImageTk
import PIL.ImageFilter
import ffmpeg
import sys
import os
import subprocess

play_watermark = PIL.Image.open(os.path.dirname(sys.argv[0]) + "/browser/images/play_watermark.png").convert("RGBA")
playing_instance = None
GAUSSIAN_BLUR_RADIUS = 25
IMAGE_SIZE =250


def clear_video():
    global playing_instance
    if playing_instance is not None:
        playing_instance.stop()
        playing_instance.clear()
        playing_instance = None


class BaseImage:
    def __init__(self):
        self.meta = {}
        raise Exception()
    def getMeta(self):
        return self.meta


class Image(tkinter.Label, BaseImage):
    def __init__(self, root, file, meta, **kwargs):
        tkinter.Label.__init__(self, root, **kwargs)
        self.meta = meta
        self.file = file
        request_obj = net.request(file)
        image = PIL.Image.open(request_obj)
        self.animated = False
        if image.format == "GIF" and ("duration" in image.info):
            self.animated = True
            self.delay = image.info["duration"]
            img = image.copy().convert("RGB")
            img.paste(
                play_watermark,
                (img.width // 2 - 24, img.height // 2 - 24),
                play_watermark
            )
            self.img_obj = PIL.ImageTk.PhotoImage(img)
            img.close()
            self.bind("<Button-1>", self.toggle_play_stop)
        else:
            self.img_obj = PIL.ImageTk.PhotoImage(image)
        self.width = image.width
        self.height = image.height
        self.frames = None
        self._current_frame = None
        self.update_frame_loop = None
        self.is_playing = False
        self["image"] = self.img_obj
        request_obj.close()
        image.close()

    def play(self):
        global playing_instance
        if playing_instance is not None and playing_instance != self:
            if playing_instance.is_playing:
                playing_instance.stop()
            playing_instance.clear()
        playing_instance = self
        if self.frames is None:
            self.frames = []
            commandline = ['ffmpeg',
                       '-i', net.request_url(self.file),
                       '-f', 'image2pipe',
                       '-pix_fmt', 'rgb24',
                        '-an',
                       '-vcodec', 'rawvideo', '-']
            ffprocess = subprocess.Popen(commandline, stdout=subprocess.PIPE)
            buffer = ffprocess.stdout.read(self.width * self.height * 3)
            while len(buffer) == self.width * self.height * 3:
                self.frames.append(PIL.ImageTk.PhotoImage(PIL.Image.frombuffer("RGB", (self.width, self.height), buffer, "raw", "RGB", 0, 1)))
                buffer = ffprocess.stdout.read(self.width * self.height * 3)
            ffprocess.stdout.close()
        self._current_frame = 0
        self.update_frame_loop = self.after(self.delay, self.update_frame())
        self.is_playing = True

    def stop(self):
        self.after_cancel(self.update_frame_loop)
        self["image"] = self.img_obj
        self.is_playing = False

    def clear(self):
        self.frames = None

    def update_frame(self):
        self["image"] = self.frames[self._current_frame]
        self._current_frame += 1
        if self._current_frame == len(self.frames):
            self._current_frame = 0
        self.update_frame_loop = self.after(self.delay, self.update_frame)

    def __del__(self):
        if self.is_playing:
            self.stop()
        self.clear()

    def toggle_play_stop(self, event):
        if self.is_playing:
            self.stop()
        else:
            self.play()
    
    def rebind(self):
        if self.animated:
            self.bind("<Button-1>", self.toggle_play_stop)


class SpoilerImage(Image, BaseImage):
    def __init__(self, root, tiny_thumb_file, file, meta, **kwargs):
        tkinter.Label.__init__(self, root, **kwargs)
        self.file = file
        self.meta = meta
        tiny_thumbnail_request = net.request(tiny_thumb_file)
        normal_thubnail_request = net.request(file)
        normal_thumbnail = PIL.Image.open(normal_thubnail_request)
        tiny_thumbnail = PIL.Image.open(tiny_thumbnail_request)
        if IMAGE_SIZE / tiny_thumbnail.width * tiny_thumbnail.height <= IMAGE_SIZE:
            tiny_thumbnail = tiny_thumbnail.resize(
                (IMAGE_SIZE, int(IMAGE_SIZE / tiny_thumbnail.width * tiny_thumbnail.height))
            )
        else:
            tiny_thumbnail = tiny_thumbnail.resize(
                (int(IMAGE_SIZE / tiny_thumbnail.height * tiny_thumbnail.width), IMAGE_SIZE)
            )
        tiny_thumbnail = tiny_thumbnail.convert("RGB")
        if normal_thumbnail.format == "GIF" and "duration" in normal_thumbnail.info:
            self.animated = True
            self.delay = normal_thumbnail.info["duration"]
            hover_img = tiny_thumbnail.copy()
            tiny_thumbnail = tiny_thumbnail.filter(PIL.ImageFilter.GaussianBlur(GAUSSIAN_BLUR_RADIUS))
            tiny_thumbnail.paste(
                play_watermark,
                (tiny_thumbnail.width // 2 - 24, tiny_thumbnail.height // 2 - 24),
                play_watermark
            )
            hover_img.paste(
                play_watermark,
                (tiny_thumbnail.width // 2 - 24, tiny_thumbnail.height // 2 - 24),
                play_watermark
            )
            self.img_obj = PIL.ImageTk.PhotoImage(tiny_thumbnail)
            self.img_obj_hover = PIL.ImageTk.PhotoImage(hover_img)
            self.bind("<Button-1>", self.toggle_play_stop)
        else:
            self.animated = False
            hover_img = tiny_thumbnail.copy()
            tiny_thumbnail = tiny_thumbnail.filter(PIL.ImageFilter.GaussianBlur(GAUSSIAN_BLUR_RADIUS))
            self.img_obj = PIL.ImageTk.PhotoImage(tiny_thumbnail)
            self.img_obj_hover = PIL.ImageTk.PhotoImage(hover_img)
            self.bind("<Button-1>", self.__show_normal_thumbnail)
        self.normal_thumbnail = PIL.ImageTk.PhotoImage(normal_thumbnail)
        self.bind("<Leave>", self.__show_spoiler)
        self.width = normal_thumbnail.width
        self.height = normal_thumbnail.height
        self.frames = None
        self._current_frame = None
        self.update_frame_loop = None
        self.is_playing = False
        self["image"] = self.img_obj
        self._img_obj = None
        self.bind("<Enter>", self.__mouse_enter)
        tiny_thumbnail.close()
        normal_thumbnail.close()
        hover_img.close()
        tiny_thumbnail_request.close()
        normal_thubnail_request.close()

    def __show_normal_thumbnail(self, event):
        self["image"] = self.normal_thumbnail

    def __mouse_enter(self, event=None):
        if not self.is_playing:
            self['image'] = self.img_obj_hover

    def __show_spoiler(self, event):
        if not self.is_playing:
            self["image"] = self.img_obj
    
    def rebind(self):
        if self.animated:
            self.bind("<Button-1>", self.toggle_play_stop)
        self.bind("<Leave>", self.__show_spoiler)
        self.bind("<Enter>", self.__mouse_enter)


class BaseVideo:
    def __init__(self):
        self.tags_meta = {}
        raise Exception()
    def getMeta(self):
        return self.tags_meta

class Video(tkinter.Label, BaseVideo):
    def __init__(self, root, file, meta, **kwargs):
        tkinter.Label.__init__(self, root, **kwargs)
        self.file = file
        self.tags_meta = meta
        ffprocess = ffmpeg.getPPM_Stream(net.request_url(file))
        pil_img = PIL.Image.open(ffprocess.stdout)
        self.width = pil_img.width
        self.height = pil_img.height
        pil_img.paste(
            play_watermark,
            (pil_img.width // 2 - 24, pil_img.height // 2 - 24),
            play_watermark
        )
        self.thumb = PIL.ImageTk.PhotoImage(pil_img)
        self["image"] = self.thumb
        self.frames = None
        self.meta = None
        self.delay = None
        self._current_frame = None
        self.update_frame_loop = None
        self.is_playing = False
        ffprocess.stdout.close()
        self.bind("<Button-1>", self.toggle_play_stop)
        pil_img.close()

    def play(self):
        global playing_instance
        if playing_instance is not None and playing_instance != self:
            if playing_instance.is_playing:
                playing_instance.stop()
            playing_instance.clear()
        if self.frames is None:
            self.frames = []
            self.meta = ffmpeg.probe(net.request_url(self.file))
            if float(self.meta['format']['duration'])<=30:
                video = None
                for stream in self.meta["streams"]:
                    if stream['codec_type'] == "video":
                        video = stream
                fps = eval(video['r_frame_rate'])
                self.delay = int(round(1 / fps * 1000))
                if self.width is None or self.height is None:
                    self.width = video["width"]
                    self.height = video["height"]
                commandline = ['ffmpeg',
                        '-i', net.request_url(self.file),
                        '-f', 'image2pipe',
                        '-pix_fmt', 'rgb24',
                        '-r', str(fps), '-an',
                        '-vcodec', 'rawvideo', '-']
                ffprocess = subprocess.Popen(commandline, stdout=subprocess.PIPE)
                buffer = ffprocess.stdout.read(self.width * self.height * 3)
                while len(buffer) == self.width * self.height * 3:
                    self.frames.append(PIL.ImageTk.PhotoImage(PIL.Image.frombuffer("RGB", (self.width, self.height), buffer, "raw", "RGB", 0, 1)))
                    buffer = ffprocess.stdout.read(self.width * self.height * 3)
                ffprocess.stdout.close()
                self._current_frame = 0
                self.update_frame_loop = self.after(self.delay, self.update_frame())
                self.is_playing = True
                playing_instance = self
            else:
                subprocess.run(['ffplay', net.request_url(self.file)])

    def stop(self):
        self.after_cancel(self.update_frame_loop)
        self["image"] = self.thumb
        self.is_playing = False

    def clear(self):
        self.frames = None

    def update_frame(self):
        self["image"] = self.frames[self._current_frame]
        self._current_frame += 1
        if self._current_frame == len(self.frames):
            self._current_frame = 0
        self.update_frame_loop = self.after(self.delay, self.update_frame)

    def __del__(self):
        if self.is_playing:
            self.stop()
        self.clear()

    def toggle_play_stop(self, event):
        if self.is_playing:
            self.stop()
        else:
            self.play()
    
    def rebind(self):
        self.bind("<Button-1>", self.toggle_play_stop)


class SpoilerVideo(Video, BaseVideo):
    def __init__(self, root, file, thumb_file, meta, **kwargs):
        tkinter.Label.__init__(self, root, **kwargs)
        self.file = file
        self.tags_meta = meta
        ffprocess = ffmpeg.getPPM_Stream(net.request_url(thumb_file))
        default_image = PIL.Image.open(ffprocess.stdout)
        self.width = None
        self.height = None
        if IMAGE_SIZE / default_image.width * default_image.height <= IMAGE_SIZE:
            default_image = default_image.resize(
                (IMAGE_SIZE, int(IMAGE_SIZE / default_image.width * default_image.height))
            )
        else:
            default_image = default_image.resize(
                (int(IMAGE_SIZE / default_image.height * default_image.width), IMAGE_SIZE)
            )
        hover_image = default_image.copy()
        default_image = default_image.filter(PIL.ImageFilter.GaussianBlur(GAUSSIAN_BLUR_RADIUS))
        default_image.paste(
            play_watermark,
            (default_image.width // 2 - 24, default_image.height // 2 - 24),
            play_watermark
        )
        hover_image.paste(
            play_watermark,
            (default_image.width // 2 - 24, default_image.height // 2 - 24),
            play_watermark
        )
        self.thumb = PIL.ImageTk.PhotoImage(default_image)
        self.thumb_hover = PIL.ImageTk.PhotoImage(hover_image)
        self["image"] = self.thumb
        self.frames = None
        self.meta = None
        self.delay = None
        self._current_frame = None
        self.update_frame_loop = None
        self.is_playing = False
        self.bind("<Leave>", self.__show_spoiler)
        self.bind("<Enter>", self.__mouse_enter)
        ffprocess.stdout.close()
        default_image.close()
        hover_image.close()
        self.bind("<Button-1>", self.toggle_play_stop)

    def __mouse_enter(self, event=None):
        if not self.is_playing:
            self['image'] = self.thumb_hover

    def __show_spoiler(self, event):
        if not self.is_playing:
            self["image"] = self.thumb

    def rebind(self):
        self.bind("<Leave>", self.__show_spoiler)
        self.bind("<Enter>", self.__mouse_enter)
        self.bind("<Button-1>", self.toggle_play_stop)
