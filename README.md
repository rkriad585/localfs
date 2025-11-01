# localfs 📂✨

A simple, fast, and beautiful local file sharing service built with Python and Flask. `localfs` helps you instantly share your media library (videos, images, etc.) across your local network through a clean, modern web interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/)
[![Made with](https://img.shields.io/badge/Made%20with-Flask%20%26%20TailwindCSS-orange.svg)](https://flask.palletsprojects.com/)

---

## 🚀 Features

*   **🌐 Instant Web Access:** View and download your files from any device on your network using a web browser.
*   **🎬 Video Player & Thumbnails:** Play videos directly in the browser and see auto-generated thumbnails for your video files.
*   **🔎 Live Search:** Instantly find the file you're looking for with a responsive search bar.
*   **🎨 Clean & Modern UI:** A beautiful, user-friendly interface built with Tailwind CSS.
*   **🔧 Highly Configurable:** Easily control which file types are shared through a simple configuration file.
*   **🔐 Optional Security:** Secure your web interface with a randomly generated access key.
*   **🤖 Smart Dependency Handling:** Automatically detects and offers to install missing Python packages (`Flask`, `rich`, `click`).
*   **📊 JSON API:** An optional API endpoint to share user activity logs securely with an API key.
*   **🖥️ Beautiful Terminal Output:** Uses the `rich` library for clean and colorful logs, errors, and startup information.

---

## ⚙️ Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Python 3.6+** and **pip**
2.  **Git** (for cloning the repository)
3.  **FFmpeg:** This is **required** for generating video thumbnails.

#### How to Install FFmpeg:
*   **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add the `bin` directory to your system's PATH.
*   **macOS (using Homebrew):**
    ```bash
    brew install ffmpeg
    ```
*   **Linux (Debian/Ubuntu):**
    ```bash
    sudo apt update && sudo apt install ffmpeg
    ```
*   **Linux (Fedora/CentOS):**
    ```bash
    sudo dnf install ffmpeg
    ```

---

## 📦 Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/rkstudio585/localfs.git
    cd localfs
    ```

2.  **Add your files:**
    Place any videos, images, or other files you want to share into the `media/` folder.

3.  **Run the application:**
    ```bash
    python main.py
    ```
    The first time you run it, the script will check for required Python libraries (Flask, Rich, Click). If they are missing, it will ask for your permission to install them automatically. Simply type `Y` and press Enter.

---

## ▶️ How to Run & Use

There are two ways to run the server:

### 1. Standard Mode (No API)

This is the simplest way to start the server.

```bash
python main.py
```

The terminal will display the access information:

```text
Starting localfs server...
 * Media Folder: /path/to/your/project/localfs/media
 * Website Access Key: e4a2b1c8d...
 * Access URL: http://127.0.0.1:5000/?key=e4a2b1c8d...
 * API Enabled: No
Press CTRL+C to stop the server.
```

*   **Access the Website:** Open your web browser and navigate to the **Access URL** provided in the terminal. This URL includes the required security key.

### 2. Share Mode (With API Enabled)

This mode starts the server and also enables the `/api` endpoint for sharing logged data.

```bash
python main.py --share
# or using the short flag
python main.py -s
```

The terminal will display an additional line with the API key:

```text
Starting localfs server...
 * Media Folder: /path/to/your/project/localfs/media
 * Website Access Key: e4a2b1c8d...
 * Access URL: http://127.0.0.1:5000/?key=e4a2b1c8d...
 * API Key: e4a2b1c8d...
Press CTRL+C to stop the server.
```

*   **Access the API:** You can now access the logged data using a tool like `curl` or your browser:
    ```bash
    curl "http://127.0.0.1:5000/api?key=YOUR_API_KEY_HERE"
    ```

### How It Works

*   **Playing Videos:** On the webpage, click the "Play" button or the video thumbnail to open a dedicated video player page.
*   **Downloading Files:** Click the "Download" button on any file card to save it to your device.
*   **Searching:** Use the search bar at the top to filter files by name in real-time.
*   **Sharing on Your Network:** To access `localfs` from another device (like a phone or tablet), replace `127.0.0.1` with your computer's local IP address (e.g., `http://192.168.1.10:5000/?key=...`).

---

## 🛠️ Configuration

You can customize the application's behavior by editing the `config.py` file.

| Setting                       | Description                                                                                                                              | Default Value                                   |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `HOST`                        | The network address to host on. `0.0.0.0` makes it accessible on your local network.                                                      | `"0.0.0.0"`                                     |
| `PORT`                        | The port for the web server.                                                                                                             | `5000`                                          |
| `ALLOWED_EXTENSIONS`          | A space-separated list of file extensions to share (e.g., `.mp4 .mkv .jpg`). Leave empty (`""`) to share all files.                       | `".mkv .mp4 .jpg .jpeg .png .gif"`               |
| `WEBSITE_ACCESS_KEY_REQUIRED` | If `True`, the website is protected by the API key. If `False`, anyone on the network can view the website without a key.                  | `True`                                          |
| `API_KEY`                     | A secure, random key generated on each startup. Used for both website and API access.                                                    | `secrets.token_hex(16)`                         |

---

## 📂 Project Structure

```
localfs/
├── main.py             # Main application logic and Flask routes
├── config.py           # All configurations
├── requirements.txt    # List of Python dependencies
├── README.md           # You are here!
│
├── data/               # Stores logs and data (auto-created)
│   └── localfs-data.json
│
├── media/              # <-- Place your files to share here
│
├── static/
│   ├── js/
│   │   └── main.js     # JavaScript for search functionality
│   └── thumbnails/     # Stores auto-generated video thumbnails
│
└── templates/
    ├── index.html      # Main homepage template
    └── player.html     # Video player page template
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/rkstudio585/localfs/issues).

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
