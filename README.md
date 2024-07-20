# MediaLib
A Collection Manager built on the excellent `exiftool`, written in QT

## Features
MediaLib gets out of your way and shows you metadata information that's relevant to the files you are viewing. However, you can leverage its powerful database and SQL-like search tools to build large libraries of all your media with support for search, export and preview
- [x] Support for different views (json, table)
- [x] Support for different video, audio and image formats. For a full list of supported formats, run `exiftool -listf` on the command line

## Installation
TODO

## TODO
### Currently working on
- Searching using DuckDB
- Tests

### Backlog
- DB support
  - Save database
    - Supported Views
    - Default View
    - Custom plugins per MimeType i.e Images: Dupe Finder
    - Previews for images, videos and music
    - Custom `exiftool` Formats
    - Private database [Which MediaLib will not track in registry]
    - Support for search, export and preview
- Map view
- Thumb view
- Nemo app integration
- SQL searching of in-memory databases

### Done
- [x] Remove toolbar and make it a menu instead
- [x] Default icons
- [x] Menu Support (Removed toolbar and moved all app functionality to menu)
- DB support
  - [x] Library View
  - Save database
    - [x] DB Name
    - [x] DB Paths