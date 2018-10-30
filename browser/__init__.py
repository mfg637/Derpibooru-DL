from . import net, images, gui

def pil_unlook_load_truncated_images():
    import PIL.ImageFile
    PIL.ImageFile.LOAD_TRUNCATED_IMAGES = True

pil_unlook_load_truncated_images()