# MediaLib
A Collection Manager built on the excellent `exiftool`, written in QT

## Features
MediaLib gets out of your way and shows you metadata information that's relevant to the files you are viewing. However, you can leverage its powerful database and SQL-like search tools to build large libraries of all your media with support for search, export and preview
- [x] Support for different representations (json, table)
- [x] Support for different video, audio and image formats. For a full list of supported formats, run `exiftool -listf` on the command line

## Installation
TODO

## TODO
### Currently work priority

1. Rename database to Collection
2. Rename Path to volume
3. Dynamic Menus
4. Support for really large collections
5. Export data
6. Paginated results
7. Find in virtual table
8. Private Collections
9. System diagram using Mermaid
10. Data diagram using Mermaid
11. Encrypted collections
12. Cached preview objects

### Backlog
- DB support
  - Preferred Views (Audio, Video, Image specific columns)
  - Default View
  - Support for search, export and preview
  - Private database (Which cannot be bookmarked or show up in history)
  - Save database
    - Storing fingerprints for images, videos and music
    - Custom `exiftool` Formats
- Improve performance of views
- Map view
- Thumb view
- Custom plugins per MimeType i.e Images: Dupe Finder
- Nemo app integration
- SQL searching of in-memory databases

### Done
- [x] Remove toolbar and make it a menu instead
- [x] Default icons
- [x] Menu Support (Removed toolbar and moved all app functionality to menu)
- [x] Adjusting log levels for better logs
- DB support
  - [x] Library View
  - [x] Close Database
  - Save database
    - [x] DB Name
    - [x] DB Paths
- [x] Showing user-selected fields and field presets
- [x] Searching using DuckDB
- [x] Core logic tests
- [x] Setup Coverage
- [x] Component testing
- [x] Fast load of JSON views