#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ********************************************************************
# ZYNTHIAN PROJECT: Zynthian Standalone Help Server
#
# Help Standalone Server
#
# Copyright (C) 2026 Fernando Moyano <jofemodo@zynthian.org>
#
# ********************************************************************
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ********************************************************************

import os
import sys
import asyncio
import logging
import tornado.web
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup

# ------------------------------------------------------------------------------
# Configure Logging
# ------------------------------------------------------------------------------

log_level = logging.INFO
#log_level = logging.DEBUG
#log_level = logging.ERROR

# Set root logging level
logging.basicConfig(format='%(levelname)s:%(module)s: %(message)s',
                    stream=sys.stderr, level=log_level)
logging.getLogger().setLevel(level=log_level)

# ------------------------------------------------------------------------------

zynthian_help_port = 8087

zynthian_help_dir = str(Path(__file__).parent.parent.resolve())
MAX_STREAMED_SIZE = 1000000

logging.info(f"Running in '{zynthian_help_dir}'")
logging.info(f"Listening at port {zynthian_help_port}")

# ------------------------------------------------------------------------------
# Help Topic Handler
# ------------------------------------------------------------------------------

class HelpHandler(tornado.web.RequestHandler):

    layout = "Z2"

    def get(self, subdir=None, html_file=None, errors=None):

        self.layout = self.get_cookie("layout", default="Z2")
        logging.info(f"Layout: {self.layout}")

        if html_file is None:
            if subdir is None:
                html_file = ""
                html = self.get_index()
            else:
                html_file = subdir
                html = self.get_content(html_file)
        else:
            html = self.get_content(html_file)

        config = {
            "layout": self.layout,
            "html_file": html_file,
            "content": html,
        }
        self.render(zynthian_help_dir + "/server/template.html", config=config)

    def post(self, subdir, html_file):
        self.get(subdir, html_file)

    def get_index(self):
        def get_data(files):
            items = []
            for file in files:
                with open(file, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f, "html.parser")
                    # Try <title> first
                    title_tag = soup.find("title")
                    title = title_tag.get_text(strip=True) if title_tag else None
                    # Fallback to <h1>
                    if not title:
                        h1 = soup.find("h1")
                        title = h1.get_text(strip=True) if h1 else file.stem
                    items.append((title, file._str))
            return items

        files = list(Path(f"{zynthian_help_dir}/common").glob("*.html")) + \
                list(Path(f"{zynthian_help_dir}/{self.layout}").glob("*.html"))
        files.sort(key=lambda f: f.name)

        # Build index HTML
        html_output = f"""
  <link rel="stylesheet" href="/help_files/style_webconf.css">
  <div class="help_ui">
  <h1>Index</h1>
  <ul class="index">
"""
        for title, filename in get_data(files):
            fpath = Path(filename)
            #href = fpath.parent.name + "/" + fpath.name
            href = fpath.name
            html_output += f'    <li><a href="{href}">{title}</a></li>\n'
        html_output += """
  </ul>
  </div>
"""
        return html_output

    def get_content(self, html_file):
        fpath_lay = f"{zynthian_help_dir}/{self.layout}/{html_file}"
        fpath_com = f"{zynthian_help_dir}/common/{html_file}"
        if os.path.isfile(fpath_lay):
            fpath = fpath_lay
            subdir = self.layout
        elif os.path.isfile(fpath_com):
            fpath = fpath_com
            subdir = "common"
        else:
            return f"<h3>Content '{html_file}' not found!</h3>"

        try:
            with open(fpath, "r") as f:
                html = f.read()
                html = self.get_body(html, subdir, fname= os.path.splitext(html_file)[0])
        except Exception as e:
            html = f"<h3>Can't parse HTML content from '{fpath}'</h3>"
            logging.error(e)

        return html

    def get_body(self, html, subdir=None, fname=None):
        soup = BeautifulSoup(html, "html.parser")
        # Get list of css files
        css_fpaths = []
        for link in soup.find_all("link", href=True):
            href = link["href"]
            css_fpath = "/help_files/"
            if subdir:
                css_fpath += subdir + "/"
            css_fpath += urllib.parse.quote(href)
            link["href"] = css_fpath
            css_fpaths.append(css_fpath)
        # Fix img's src'
        for img in soup.find_all("img", src=True):
            src = "/help_files/"
            if subdir:
                src += subdir + "/"
            img["src"] = src + urllib.parse.quote(img["src"])
        # Fix link's href
        for link in soup.find_all("a", href=True):
            href = link["href"].replace(zynthian_help_dir, "")
            link["href"] = urllib.parse.quote(href)
        # Generate html adding css
        html = ""
        for css_fpath in css_fpaths:
            html += f"<link rel=\"stylesheet\" href=\"{css_fpath}\">\n"
        html += "<link rel=\"stylesheet\" href=\"/help_files/style_webconf.css\">"
        html += "<div class=\"help_ui\">\n"
        if fname:
            fpath_lay = f"screenshots/{self.layout}/{fname}"
            fpath_com = f"screenshots/common/{fname}"
            if os.path.isfile(zynthian_help_dir + "/" + fpath_lay + ".mp4"):
                html += f"<video class='screenshot' controls autoplay muted loop><source src=\"/help_files/{fpath_lay}.mp4\" type='video/mp4'></video>\n"
            elif os.path.isfile(zynthian_help_dir + "/" + fpath_lay + ".png"):
                html += f"<img class='screenshot' src=\"/help_files/{fpath_lay}.png\"/>\n"
            elif os.path.isfile(zynthian_help_dir + "/" + fpath_lay + ".jpg"):
                html += f"<img class='screenshot' src=\"/help_files/{fpath_lay}.jpg\"/>\n"
            elif os.path.isfile(zynthian_help_dir + "/" + fpath_com + ".mp4"):
                html += f"<video class='screenshot' controls autoplay muted loop><source src=\"/help_files/{fpath_com}.mp4\" type='video/mp4'></video>\n"
            elif os.path.isfile(zynthian_help_dir + "/" + fpath_com + ".png"):
                html += f"<img class='screenshot' src=\"/help_files/{fpath_com}.png\"/>\n"
            elif os.path.isfile(zynthian_help_dir + "/" + fpath_com + ".jpg"):
                html += f"<img class='screenshot' src=\"/help_files/{fpath_com}.jpg\"/>\n"
        html += soup.body.decode_contents()
        html += "\n</div>"
        return html

# ------------------------------------------------------------------------------
# Build Web App & Start Server
# ------------------------------------------------------------------------------

def make_app():
    settings = {
        "template_path": "templates",
        "template_whitespace": "single",
        # "autoescape": None
    }

    return tornado.web.Application([
        (r"/help_files/(.*)$", tornado.web.StaticFileHandler, {'path': zynthian_help_dir}),
        (r"/icons/(.*)$", tornado.web.StaticFileHandler, {'path': zynthian_help_dir + '/icons'}),
        (r"/fonts/(.*)$", tornado.web.StaticFileHandler, {'path': zynthian_help_dir + '/fonts'}),
        (r"/img/(.*)$", tornado.web.StaticFileHandler, {'path': zynthian_help_dir + '/img'}),
        (r"/css/(.*)$", tornado.web.StaticFileHandler, {'path': zynthian_help_dir + '/css'}),
        (r"/js/(.*)$", tornado.web.StaticFileHandler, {'path': zynthian_help_dir + '/js'}),
        (r"/$", HelpHandler),
        (r"/(.*)$", HelpHandler),
        (r"/(.*)/(.*)$", HelpHandler)
    ], **settings)

async def amain():
    app = make_app()
    app.listen(zynthian_help_port, max_body_size=MAX_STREAMED_SIZE)
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        print("Shutting down on SIGINT")

# ------------------------------------------------------------------------------
