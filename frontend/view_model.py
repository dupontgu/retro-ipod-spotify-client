import spotify_manager
import re as re
from functools import lru_cache 

MENU_PAGE_SIZE = 6

# Screen render types
MENU_RENDER_TYPE = 0
NOW_PLAYING_RENDER = 1
SEARCH_RENDER = 2

# Menu line item types
LINE_NORMAL = 0
LINE_HIGHLIGHT = 1
LINE_TITLE = 2

spotify_manager.refresh_devices()

class LineItem():
    def __init__(self, title = "", line_type = LINE_NORMAL, show_arrow = False):
        self.title = title
        self.line_type = line_type
        self.show_arrow = show_arrow

class Rendering():
    def __init__(self, type):
        self.type = type

    def unsubscribe(self):
        pass

class MenuRendering(Rendering):
    def __init__(self, header = "", lines = [], page_start = 0, total_count = 0):
        super().__init__(MENU_RENDER_TYPE)
        self.lines = lines
        self.header = header
        self.page_start = page_start
        self.total_count = total_count
        self.now_playing = spotify_manager.DATASTORE.now_playing
        self.has_internet = spotify_manager.has_internet

class NowPlayingRendering(Rendering):
    def __init__(self):
        super().__init__(NOW_PLAYING_RENDER)
        self.callback = None
        self.after_id = None

    def subscribe(self, app, callback):
        if callback == self.callback:
            return
        new_callback = self.callback is None
        self.callback = callback
        self.app = app
        if new_callback:
            self.refresh()

    def refresh(self):
        if not self.callback:
            return
        if self.after_id:
            self.app.after_cancel(self.after_id)
        self.callback(spotify_manager.DATASTORE.now_playing)
        self.after_id = self.app.after(500, lambda: self.refresh())

    def unsubscribe(self):
        super().unsubscribe()
        self.callback = None
        self.app = None

class NowPlayingCommand():
    def __init__(self, runnable = lambda:()):
        self.has_run = False
        self.runnable = runnable
    
    def run(self):
        self.has_run = True
        self.runnable()

class SearchRendering(Rendering):
    def __init__(self, query, active_char):
        super().__init__(SEARCH_RENDER)
        self.query = query
        self.active_char = active_char
        self.loading = False
        self.callback = None
        self.results = None

    def get_active_char(self):
        return ' ' if self.active_char == 26 else chr(self.active_char + ord('a'))

    def subscribe(self, app, callback):
        if (callback == self.callback):
            return
        new_callback = self.callback is None
        self.callback = callback
        self.app = app
        if new_callback:
            self.refresh()

    def refresh(self):
        if not self.callback:
            return
        self.callback(self.query, self.get_active_char(), self.loading, self.results)
        self.results = None

    def unsubscribe(self):
        super().unsubscribe()
        self.callback = None
        self.app = None

class SearchPage():
    def __init__(self, previous_page):
        self.header = "Search"
        self.has_sub_page = True
        self.previous_page = previous_page
        self.live_render = SearchRendering("", 0)
        self.is_title = False

    def nav_prev(self):
        self.live_render.query = self.live_render.query[0:-1]
        self.live_render.refresh()

    def nav_next(self):
        if len(self.live_render.query) > 15:
            return
        active_char = ' ' if self.live_render.active_char == 26 \
          else chr(self.live_render.active_char + ord('a')) 
        self.live_render.query += active_char
        self.live_render.refresh()

    def nav_play(self):
        pass

    def nav_up(self):
        self.live_render.active_char += 1
        if (self.live_render.active_char > 26):
            self.live_render.active_char = 0
        self.live_render.refresh()

    def nav_down(self):
        self.live_render.active_char -= 1
        if (self.live_render.active_char < 0):
            self.live_render.active_char = 26
        self.live_render.refresh()

    def run_search(self, query):
        self.live_render.loading = True
        self.live_render.refresh()
        self.live_render.results = spotify_manager.search(query)
        self.live_render.loading = False
        self.live_render.refresh()

    def nav_select(self):
        spotify_manager.run_async(lambda: self.run_search(self.live_render.query))
        return self

    def nav_back(self):
        return self.previous_page

    def render(self):
        return self.live_render

class NowPlayingPage():
    def __init__(self, previous_page, header, command):
        self.has_sub_page = False
        self.previous_page = previous_page
        self.command = command
        self.header = header
        self.live_render = NowPlayingRendering()
        self.is_title = False

    def play_previous(self):
        spotify_manager.play_previous()
        self.live_render.refresh()

    def play_next(self):
        spotify_manager.play_next()
        self.live_render.refresh()

    def toggle_play(self):
        spotify_manager.toggle_play()
        self.live_render.refresh()

    def nav_prev(self):
        spotify_manager.run_async(lambda: self.play_previous()) 

    def nav_next(self):
        spotify_manager.run_async(lambda: self.play_next()) 

    def nav_play(self):
        spotify_manager.run_async(lambda: self.toggle_play()) 

    def nav_up(self):
        pass

    def nav_down(self):
        pass

    def nav_select(self):
        return self

    def nav_back(self):
        return self.previous_page

    def render(self):
        if (not self.command.has_run):
            self.command.run()
        return self.live_render

EMPTY_LINE_ITEM = LineItem()
class MenuPage():
    def __init__(self, header, previous_page, has_sub_page, is_title = False):
        self.index = 0
        self.page_start = 0
        self.header = header
        self.has_sub_page = has_sub_page
        self.previous_page = previous_page
        self.is_title = is_title

    def total_size(self):
        return 0

    def page_at(self, index):
        return None

    def nav_prev(self):
        spotify_manager.run_async(lambda: spotify_manager.play_previous()) 

    def nav_next(self):
        spotify_manager.run_async(lambda: spotify_manager.play_next()) 

    def nav_play(self):
        spotify_manager.run_async(lambda: spotify_manager.toggle_play()) 
    
    def get_index_jump_up(self):
        return 1

    def get_index_jump_down(self):
        return 1

    def nav_up(self):
        jump = self.get_index_jump_up()
        if(self.index >= self.total_size() - jump):
            return
        if (self.index >= self.page_start + MENU_PAGE_SIZE - jump):
            self.page_start = self.page_start + jump
        self.index = self.index + jump

    def nav_down(self):
        jump = self.get_index_jump_down()
        if(self.index <= (jump - 1)):
            return
        if (self.index <= self.page_start + (jump - 1)):
            self.page_start = self.page_start - jump
            if (self.page_start == 1):
                self.page_start = 0
        self.index = self.index - jump

    def nav_select(self):
        return self.page_at(self.index)

    def nav_back(self):
        return self.previous_page

    def render(self):
        lines = []
        total_size = self.total_size()
        for i in range(self.page_start, self.page_start + MENU_PAGE_SIZE):
            if (i < total_size):
                page = self.page_at(i)
                if (page is None) :
                    lines.append(EMPTY_LINE_ITEM)
                else:
                    line_type = LINE_TITLE if page.is_title else \
                        LINE_HIGHLIGHT if i == self.index else LINE_NORMAL
                    lines.append(LineItem(page.header, line_type, page.has_sub_page))
            else:
                lines.append(EMPTY_LINE_ITEM)
        return MenuRendering(lines=lines, header=self.header, page_start=self.index, total_count=total_size)

class PlaylistsPage(MenuPage):
    def __init__(self, previous_page):
        super().__init__(self.get_title(), previous_page, has_sub_page=True)
        self.playlists = self.get_content()
        self.num_playlists = len(self.playlists)
                
        self.playlists.sort(key=self.get_idx) # sort playlists to keep order as arranged in Spotify library

    def get_title(self):
        return "Playlists"

    def get_content(self):
        return spotify_manager.DATASTORE.getAllSavedPlaylists()

    def get_idx(self, e): # function to get idx from UserPlaylist for sorting
        if type(e) == spotify_manager.UserPlaylist: # self.playlists also contains albums as it seems and they don't have the idx value
            return e.idx
        else:
            return 0

    def total_size(self):
        return self.num_playlists

    @lru_cache(maxsize=15)
    def page_at(self, index):
        return SinglePlaylistPage(self.playlists[index], self)

class AlbumsPage(PlaylistsPage):
    def __init__(self, previous_page):
        super().__init__(previous_page)

    def get_title(self):
        return "Albums"

    def get_content(self):
        return spotify_manager.DATASTORE.getAllSavedAlbums()

class SearchResultsPage(MenuPage):
    def __init__(self, previous_page, results):
        super().__init__("Search Results", previous_page, has_sub_page=True)
        self.results = results
        tracks, albums, artists = len(results.tracks), len(results.albums), len(results.artists)
        # Add 1 to each count (if > 0) to make room for section header line items 
        self.tracks = tracks + 1 if tracks > 0 else 0
        self.artists = artists + 1 if artists > 0 else 0
        self.albums = albums + 1 if albums > 0 else 0
        self.total_count = self.tracks + self.albums + self.artists
        self.index = 1
        # indices of the section header line items
        self.header_indices = [0, self.tracks, self.artists + self.tracks]

    def total_size(self):
        return self.total_count

    def page_at(self, index):
        if self.tracks > 0 and index == 0:
            return PlaceHolderPage("TRACKS", self, has_sub_page=False, is_title=True)
        elif self.artists > 0 and index == self.header_indices[1]:
            return PlaceHolderPage("ARTISTS", self, has_sub_page=False, is_title=True)
        elif self.albums > 0 and index == self.header_indices[2]:
            return PlaceHolderPage("ALBUMS", self, has_sub_page=False, is_title=True)
        elif self.tracks > 0 and  index < self.header_indices[1]:
            track = self.results.tracks[index - 1]
            command = NowPlayingCommand(lambda: spotify_manager.play_track(track.uri))
            return NowPlayingPage(self, track.title, command)
        elif self.albums > 0 and  index < self.header_indices[2]:
            artist = self.results.artists[index - (self.tracks + 1)]
            command = NowPlayingCommand(lambda: spotify_manager.play_artist(artist.uri))
            return NowPlayingPage(self, artist.name, command)
        else:
            album = self.results.albums[index - (self.artists + self.tracks + 1)]
            tracks = self.results.album_track_map[album.uri]
            return InMemoryPlaylistPage(album, tracks, self)

    def get_index_jump_up(self):
        if self.index + 1 in self.header_indices:
            return 2
        return 1

    def get_index_jump_down(self):
        if self.index - 1 in self.header_indices:
            return 2
        return 1

class NewReleasesPage(PlaylistsPage):
    def __init__(self, previous_page):
        super().__init__(previous_page)

    def get_title(self):
        return "New Releases"

    def get_content(self):
        return spotify_manager.DATASTORE.getAllNewReleases()

class ArtistsPage(MenuPage):
    def __init__(self, previous_page):
        super().__init__("Artists", previous_page, has_sub_page=True)

    def total_size(self):
        return spotify_manager.DATASTORE.getArtistCount()

    def page_at(self, index):
        # play track
        artist = spotify_manager.DATASTORE.getArtist(index)
        command = NowPlayingCommand(lambda: spotify_manager.play_artist(artist.uri))
        return NowPlayingPage(self, artist.name, command)
    
class SingleArtistPage(MenuPage):
    def __init__(self, artistName, previous_page):
        super().__init__(artistName, previous_page, has_sub_page=True)

class SinglePlaylistPage(MenuPage):
    def __init__(self, playlist, previous_page):
        # Credit for code to remove emoticons from string: https://stackoverflow.com/a/49986645
        regex_pattern = re.compile(pattern = "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                            "]+", flags = re.UNICODE)

        super().__init__(regex_pattern.sub(r'',playlist.name), previous_page, has_sub_page=True)
        self.playlist = playlist
        self.tracks = None

    def get_tracks(self):
        if self.tracks is None:
            self.tracks = spotify_manager.DATASTORE.getPlaylistTracks(self.playlist.uri)
        return self.tracks

    def total_size(self):
        return self.playlist.track_count

    def page_at(self, index):
        track = self.get_tracks()[index]
        command = NowPlayingCommand(lambda: spotify_manager.play_from_playlist(self.playlist.uri, track.uri, None))
        return NowPlayingPage(self, track.title, command)

class InMemoryPlaylistPage(SinglePlaylistPage):
    def __init__(self, playlist, tracks, previous_page):
        super().__init__(playlist, previous_page)
        self.tracks = tracks

class SingleTrackPage(MenuPage):
    def __init__(self, track, previous_page, playlist = None, album = None):
        super().__init__(track.title, previous_page, has_sub_page=False)
        self.track = track
        self.playlist = playlist
        self.album = album

    def render(self):
        r = super().render()
        print("render track")
        context_uri = self.playlist.uri if self.playlist else self.album.uri
        spotify_manager.play_from_playlist(context_uri, self.track.uri, None)
        return r

class SavedTracksPage(MenuPage):
    def __init__(self, previous_page):
        super().__init__("Saved Tracks", previous_page, has_sub_page=True)

    def total_size(self):
        return spotify_manager.DATASTORE.getSavedTrackCount()

    def page_at(self, index):
        # play track
        return SingleTrackPage(spotify_manager.DATASTORE.getSavedTrack(index), self)

class PlaceHolderPage(MenuPage):
    def __init__(self, header, previous_page, has_sub_page=True, is_title = False):
        super().__init__(header, previous_page, has_sub_page, is_title)

class RootPage(MenuPage):
    def __init__(self, previous_page):
        super().__init__("sPot", previous_page, has_sub_page=True)
        self.pages = [
            ArtistsPage(self),
            AlbumsPage(self),
            NewReleasesPage(self),
            PlaylistsPage(self),
            SearchPage(self),
            NowPlayingPage(self, "Now Playing", NowPlayingCommand())
        ]
        self.index = 0
        self.page_start = 0
    
    def get_pages(self):
        if (not spotify_manager.DATASTORE.now_playing):
            return self.pages[0:-1]
        return self.pages
    
    def total_size(self):
        return len(self.get_pages())

    def page_at(self, index):
        return self.get_pages()[index]


    
