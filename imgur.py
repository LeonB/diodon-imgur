# -*- coding: utf-8 -*-
# ex:set ts=4 et sw=4 ai:

# Author: Leon Bogaert <leon AT tim-online DOT nl>
# This Plugin adds an "Upload to imgur menu item in the diodon menu whenever
# an image is selected in the clipboard
# It depends on pycurl and the stdlib
# Tested on diodon 0.7.0
# Released under GNU GPL v2
#
# 2012-09-12, Leon <leon AT tim-online DOT nl>:
#     version 0.0.1 Intial release
#
# @TODO: implement error handling :)
# @TODO: look into new get_current_item(type) (implement in do_activate)
# @TODO: add more links?!
##

import pycurl
import cStringIO
from xml.etree import ElementTree
import re
from gi.repository import GObject
from gi.repository import Peas
from gi.repository import Diodon
from gi.repository import Gtk
from gi.repository import GObject
GObject.threads_init()

class ImgurPlugin(GObject.Object, Peas.Activatable):
    __gtype_name__ = 'ImgurPlugin'

    object = GObject.property(type=GObject.Object)

    def do_activate(self):
        controller = self.object
        self.menu_item = Gtk.MenuItem("Upload to imgur")
        self.menu_item.connect('activate', self.on_menu_item_activate)

        self.clipboard_item = None

        if hasattr(controller, 'get_current_item'):
            self.clipboard_item = controller.get_current_item()
            self.add_imgur_menu_item()

        controller.connect('on_add_item', self.on_add_item)

    def on_menu_item_activate(self, menu_item):
        UploadWindow(self.clipboard_item.get_clipboard_data())

    def on_add_item(self, controller, clipboard_item):
        if isinstance(clipboard_item, Diodon.ImageClipboardItem):
            self.clipboard_item = clipboard_item
            self.add_imgur_menu_item(controller)
        else:
            self.clipboard_item = None
            self.remove_imgur_menu_item(controller)

    def add_imgur_menu_item(self, controller):
        menu = controller.get_menu()
        menu.insert(self.menu_item, len(menu)-1)

        menu.show_all()

    def remove_imgur_menu_item(self, controller):
        controller.get_menu().remove(self.menu_item)

    def do_deactivate(self):
        controller = self.object

    def do_update_state(self):
        controller = self.object


class UploadWindow(Gtk.Window):
    def __init__(self, path):
        super(UploadWindow, self).__init__()

        self.set_size_request(250, 50)
        self.set_title("Uploading to Imgur")
        self.set_border_width(0)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.vbox = Gtk.VBox(False, 5)
        self.vbox.set_border_width(10)
        self.add(self.vbox)
        self.vbox.show()

        # Create a centering alignment object
        align = Gtk.Alignment()
        self.vbox.pack_start(align, False, False, 5)
        align.show()

        # Create the ProgressBar
        self.pbar = Gtk.ProgressBar()
        align.add(self.pbar)
        self.pbar.show()

        self.show()


        self.uploader = Uploader(path)

        import threading
        t = threading.Thread(None, self.uploader.run, None, (self.progress_callback, self.ready_callback))
        t.start()
        print 'na thread start!'

        self.connect("destroy", self.on_destroy)

    def progress_callback(self, download_t, download_d, upload_t, upload_d):
        try:
            return self.pbar.set_fraction(float(upload_d)/float(upload_t))
        except ZeroDivisionError:
            return 0

    def ready_callback(self):
        headers =  self.uploader.headers.getvalue()
        m = re.findall('HTTP/\d\.\d\s+(\d+)\s+.*', headers)
        m.reverse()
        http_status = int(m[0])

        if http_status != 200:
            raise Exception('Bad http status code', http_status)

        xml = self.uploader.response.getvalue()
        link = ElementTree.fromstring(xml).find('links').find('imgur_page').text
        link_button = Gtk.LinkButton(link, link)
        self.vbox.add(link_button)
        link_button.show()

    def on_destroy(self, window):
        pass

class Uploader(object):
    imgur_url =  "http://api.imgur.com/2/upload.xml"
    api_key = '64bc5ce6cd6decff52545acc065dddd6'

    def __init__(self, path):
        self.path = path
        self.response = cStringIO.StringIO()
        self.headers = cStringIO.StringIO()

    def progress(self, download_t, download_d, upload_t, upload_d):
        # download_t: total to download
        # download_d: total downloaded
        # upload_t: total to upload
        # upload_d: total uploaded

        return self.progress_callback(download_t, download_d, upload_t, upload_d)

    def run(self, progress_callback, ready_callback):
        self.progress_callback = progress_callback
        self.ready_callback = ready_callback

        c = pycurl.Curl()
        values = [
            ("key", self.api_key),
            ("image", (c.FORM_FILE, self.path))]

        c.setopt(c.URL, self.imgur_url)
        c.setopt(c.HTTPPOST, values)
        c.setopt(c.NOPROGRESS, 0)
        c.setopt(c.PROGRESSFUNCTION, self.progress)
        c.setopt(c.WRITEFUNCTION, self.response.write)
        c.setopt(c.HEADERFUNCTION, self.headers.write)

        c.perform()
        c.close()

        GObject.idle_add(self.ready_callback) #in main thread uitvoeren
