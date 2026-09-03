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
zynthian_layout = "Z2"
MAX_STREAMED_SIZE = 1000000

logging.info(f"Running in '{zynthian_help_dir}'")
logging.info(f"Listening at port {zynthian_help_port}")

# ------------------------------------------------------------------------------
# Help Topic Handler
# ------------------------------------------------------------------------------

class HelpHandler(tornado.web.RequestHandler):

    def get(self, subdir=None, html_file=None, errors=None):
        if subdir is None and html_file is None:
            subdir = ""
            html_file = ""
            html = self.get_body(self.get_index())
            index = True
        else:
            html = self.get_content(subdir, html_file)
            index = False

        config = {
            "subdir": subdir,
            "html_file": html_file,
            "content": html,
            "index": index
        }

        if not config['index']:
            index_link = "<br/>"
        else:
            index_link = ""

        self.set_header("Content-Type", "text/html")
        self.write(f"""<!DOCTYPE html>
<html>
 <head>
  <meta charset="utf-8">
  <title>Zynthian Help</title>
  <meta name="description" content="Zynthian Help Pages">
  <link rel="shortcut icon" href="/icons/favicon.ico">
  <!-- Touch Icons - iOS and Android 2.1+ 180x180 pixels in size. -->
  <link rel="apple-touch-icon-precomposed" href="/icons/favicon_180.png">
  <!-- Firefox, Chrome, Safari, IE 11+ and Opera. 196x196 pixels in size. -->
  <link rel="icon" href="/icons/favicon_196.png">
  <link rel="stylesheet" href="/help_files/style_server.css">
 </head>
 <body>
 <div class="help_header">
  <div class="container"><a href=\"/\"><img src=\"/img/zynthian_logo_black_trans_320.png\"/><span>- HELP</span></a></div>
 </div>
 <div class="help_container">
 {config["content"]}
 </div>
 </body>
</html>
"""     )

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

        files = list(Path(f"{zynthian_help_dir}/core").glob("*.html")) + \
                list(Path(f"{zynthian_help_dir}/{zynthian_layout}").glob("*.html"))
        files.sort(key=lambda f: f.name)
        widgets = list(Path(f"{zynthian_help_dir}/widgets").glob("*.html"))

        # Build index HTML
        html_output = f"""
 <body class="help_ui">
  <h1>Help Index</h1>
  <ul class="index">
"""

        for title, filename in get_data(files):
            html_output += f'    <li><a href="{filename}">{title}</a></li>\n'
        html_output += """
  </ul>
  <h2>Control GUI Widgets</h2>
  <ul class="index">
"""
        for title, filename in get_data(widgets):
            html_output += f'    <li><a href="{filename}">{title}</a></li>\n'
        html_output += """
  </ul>
 </body>
</html>
"""
        return html_output

    def get_content(self, subdir, html_file):
        try:
            fpath = f"{zynthian_help_dir}/{subdir}/{html_file}"
            with open(fpath, "r") as f:
                html = f.read()
                try:
                    html = self.get_body(html, subdir, fname= os.path.splitext(html_file)[0])
                except Exception as e:
                    logging.error(e)

        except:
            html = f"<h3>Content '{subdir}/{html_file}' not found!</h3>"
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
        html += f"<link rel=\"stylesheet\" href=\"/help_files/style_webconf.css\">\n"
        html += "<div class=\"help_ui\">\n"
        if fname:
            fpath = f"{subdir}/screenshots/{fname}"
            if os.path.isfile(zynthian_help_dir + "/" + fpath + ".mp4"):
                html += f"<video class='screenshot' controls autoplay muted loop><source src=\"/help_files/{fpath}.mp4\" type='video/mp4'></video>\n"
            elif os.path.isfile(zynthian_help_dir + "/" + fpath + ".png"):
                html += f"<img class='screenshot' src=\"/help_files/{fpath}.png\"/>\n"
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
