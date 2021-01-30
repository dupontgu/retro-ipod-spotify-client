# sPot

This code is meant to accompany [this project](https://hackaday.io/project/177034-spot-spotify-in-a-4th-gen-ipod-2004) in which I build a Spotify client into an iPod "Classic" from 2004. Everything is meant to run on a Raspberry Pi Zero W.

# Instructions

1. Install updates 

```
sudo apt-get update 
sudo apt-get upgrade

```
2. Install Required Packages.

Installation for python3-pip, raspotify, python3-tk, 
```
sudo apt install python3-pip

sudo curl -sL https://dtcooper.github.io/raspotify/install.sh | sh

sudo apt-get install python3-tk 

sudo apt-get install python3-pigpio



```
3. Install Dependencies

```
pip3 install -r requirements.txt
```

4. Install pi-btaudio
```
git clone https://github.com/bablokb/pi-btaudio.git
cd pi-btaudio
sudo tools/install
```
