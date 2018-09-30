#!/bin/bash
set -x

# dt=$(date -d "1 day ago" +%Y%m%d)
dt=20100101

# Ronnie PLkP_My9q5nzD79xWxqDsbu52sqz_fuYFv
# Judd PLkP_My9q5nzDDD3Sb0vlVSYflsMt76zqZ
# ALL UUSG6QrPu4YxUJLDtTVC7cXQ
echo 'downloading video...'
youtube-dl -ci \
    -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]" \
    --write-thumbnail \
    --write-info-json \
    --dateafter $dt \
    -o "download/%(title)s#%(id)s.%(ext)s" \
    QXDzLTf8wK8

echo 'uploading video...'
python uploader.py

set +x
