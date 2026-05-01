# input/

Drop your PDFs, EPUBs, Markdown, TXT, or HTML files in here.

You can put them anywhere on your computer — the CLI just needs the path —
but this folder is the convention used in the README examples so you don't
have to type long paths or `cd` around.

```
twinktalks input/my-paper.pdf                    # default output → output/
twinktalks input/my-paper.pdf output/audio.mp3   # explicit path
twinktalks input/textbook.epub --chapters all --merge-chapters  # whole book
```

Files here are **not committed to git** (see `.gitignore`). Only this
README is tracked so the directory exists on a fresh clone.

The web UI (`twinktalks-server`) ignores this folder — it uploads through
the browser and stores files in `~/.twinktalks/uploads/`.
