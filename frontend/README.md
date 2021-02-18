# Frontend

To run: `python3 spotifypod.py`

## Dependencies

First, you'll need to install the dependencies via `pip3`:

```sh
pip3 install -r requirements.txt
```

## Authentication

You'll need to authenticate with Spotify to get an access token, which will sit in a file called `.cache`. If you try to run the app without `.cache` present, one will be generated for you, BUT it will not contain a real access token. 
Follow `spotipy`'s instructions [here](https://spotipy.readthedocs.io/en/2.16.1/#client-credentials-flow).