# MediaLib
A Collection Manager built on the excellent `exiftool`, written in QT

## Features
MediaLib gets out of your way and shows you metadata information that's relevant to the files you are viewing. However, you can leverage its powerful Collection and SQL-like search tools to build large libraries of all your media with support for search, export and preview
- [x] Support for different representations (json, table)
- [x] Support for different video, audio and image formats. For a full list of supported formats, run `exiftool -listf` on the command line

## Installation
TODO

## TODO
### Currently work priority
1. Private Collections: Zipped / Mark Private - Ctrl+Open will make DB private
2. Support for really large collections
3. Export data
4. Find in virtual table
5. System diagram using Mermaid
6. Data diagram using Mermaid
7. Encrypted collections
8. Cached preview objects

### Backlog
- DB support
  - Preferred Views (Audio, Video, Image specific columns)
  - Default View
  - Support for search, export and preview
  - Private Collection (Which cannot be bookmarked or show up in history)
  - Save Collection
    - Storing fingerprints for images, videos and music
    - Custom `exiftool` Formats
- Map view
- Thumb view
- Custom plugins per MimeType i.e Images: Dupe Finder
- Nemo app integration
- SQL searching of in-memory Collections
  - Simultaneously fire a reindex request
  - Fire a reindex when search window opens

### Done
- [x] Remove toolbar and make it a menu instead
- [x] Default icons
- [x] Menu Support (Removed toolbar and moved all app functionality to menu)
- [x] Adjusting log levels for better logs
- DB support
  - [x] Library View
  - [x] Close Collection
  - Save Collection
    - [x] DB Name
    - [x] DB Paths
- [x] Showing user-selected fields and field presets
- [x] Searching using DuckDB
- [x] Core logic tests
- [x] Setup Coverage
- [x] Component testing
- [x] Fast load of JSON views
- [x] Collection operations to be atomic, so that the DB can be queried while updates/refreshes are taking place
- [x] Dynamic Menus
- [x] Rename Collection to Collection
- [x] File System View
- [x] Improve performance of views
- [x] Support for reindexing data on demand

### Cancelled Tasks
1. ~~Rename Path to Directory~~
2. ~~Paginated results~~

### Issues
1. ~~When a new path is added to a saved collection, the info service does not work because the new path is not yet indexed~~
2. Filesystem view is hanging application. Test with 09.24.MLTEST collection