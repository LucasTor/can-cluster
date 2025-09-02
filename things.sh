sudo apt update && sudo apt install -y \
    python3-pip \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libmtdev-dev \
    libgl1-mesa-dev \
    libgles2-mesa-dev \
    libdrm-dev \
    libgbm-dev \
    libudev-dev \
    libinput-dev \
    libxkbcommon-dev \
    xserver-xorg-video-fbdev \
    evtest \
    xinput \
    fbset \
    udev \
    build-essential

sudo apt install python3-kivy

# pip3 install "kivy[base]" --no-binary :all:

export KIVY_METRICS_DENSITY=1
export KIVY_NO_CONSOLELOG=1
export KIVY_WINDOW=sdl2
export SDL_VIDEODRIVER=fbcon
export SDL_FBDEV=/dev/fb0
export KIVY_GL_BACKEND=gles

python3 main.py


[Unit]
Description=Start Kivy App at Boot (as root)
After=basic.target
Wants=basic.target

[Service]
# No 'User=' line = run as root
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/0
ExecStartPre=/bin/plymouth show-splash
ExecStart=/usr/bin/python3 /home/lucas/cluster.py
ExecStartPost=/bin/plymouth quit
Restart=on-failure
WorkingDirectory=/home/lucas
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target