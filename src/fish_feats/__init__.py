from napari.utils.notifications import show_info
import napari

def show_hello_message():
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(20)
    show_info('Hello, world!')
    print('Hello, world')
    logger.info("Message")

def start():
    from fish_feats.Naparing import openImage
    openImage()




