# IMGCRUSH

A lightweight image compression tool built with Flask and Pillow. Upload images through a clean web interface, set a target file size, and download optimized versions — all processed locally.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **Drag-and-drop uploads** — supports JPEG, PNG, and WebP
- **Target file size** — specify a size in KB or MB and the compressor will binary-search for the best quality setting to hit it
- **Format conversion** — output as JPEG, PNG, or WebP regardless of the input format
- **Resize** — optionally set width and/or height (aspect ratio preserved if only one is given)
- **Instant preview** — side-by-side before/after comparison in-browser
- **No external services** — everything runs locally on your machine

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
git clone https://github.com/torinriley/image-compression.git
cd image-compression
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install flask pillow
```

### Run

```bash
python main.py
```

Open [http://localhost:5050](http://localhost:5050) in your browser.

## How It Works

For lossy formats (JPEG, WebP), the compressor runs a binary search over quality values (1–95) to find the highest quality that stays under the target file size. PNG output uses lossless optimization instead. Uploaded files are stored in a temporary directory that gets cleaned up when the server stops.

## Project Structure

```
.
├── main.py              # Flask app + compression logic
└── templates/
    └── index.html       # Frontend (single-page, no build step)
```

## API

All endpoints are used internally by the frontend, but they're straightforward if you want to hit them directly:

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves the UI |
| `/upload` | POST | Upload an image (multipart form, field: `file`) |
| `/preview/<file_id>` | GET | Returns a thumbnail preview |
| `/compress` | POST | Compress with options (JSON body: `file_id`, `format`, `target_size`, `unit`, `resize_w`, `resize_h`) |
| `/download/<file_id>` | GET | Download the compressed file |

## Configuration

- **Max upload size** — 50 MB (set via `MAX_CONTENT_LENGTH` in `main.py`)
- **Port** — 5050 (change at the bottom of `main.py`)

## Contributing

Pull requests are welcome. For larger changes, open an issue first to discuss what you'd like to change.

## License

MIT
