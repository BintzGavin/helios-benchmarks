#!/bin/sh
exec @CHROME_BINARY@ "$@" --disable-gpu --disable-gpu-compositing --disable-gpu-rasterization
