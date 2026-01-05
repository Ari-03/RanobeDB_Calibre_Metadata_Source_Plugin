# RanobeDB Light Novels - Calibre Metadata Plugin

A Calibre metadata source plugin that downloads metadata and covers for light novels from [RanobeDB](https://ranobedb.org).

## Features

- **Search by title and author** - Find light novels in RanobeDB's extensive database
- **Direct lookup by RanobeDB ID** - Quick metadata retrieval when you have the ID
- **Cover downloads** - High-quality cover images from RanobeDB
- **Series information** - Automatically sets series name and volume number
- **Multi-language support** - Choose between English, Japanese, or Romaji titles
- **Tag extraction** - Imports genres and tags from RanobeDB
- **Rate limiting** - Respects RanobeDB's API limits (60 requests/minute)

## Metadata Fields

The plugin can download the following metadata:

| Field | Source |
|-------|--------|
| Title | Book title (configurable language) |
| Authors | Staff with "author" role |
| Publisher | First publisher listed |
| Publication Date | Release date |
| Description | Book description |
| Series | Series name |
| Series Index | Volume number in series |
| Tags | Genres and tags from series |
| ISBN | From release data |
| Cover | Book cover image |
| Language | Book language |

## Installation

### From Release (Recommended)

1. Download the latest `RanobeDB-Light-Novels.zip` from the releases page
2. Open Calibre
3. Go to **Preferences** → **Plugins** → **Load plugin from file**
4. Select the downloaded ZIP file
5. Restart Calibre

### From Source

```bash
# Clone the repository
git clone https://github.com/your-username/ranobedb-calibre-plugin.git
cd ranobedb-calibre-plugin

# Build the plugin
./build.sh

# Install to Calibre
calibre-customize -a RanobeDB-Light-Novels.zip
```

### Using UV (Development)

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync

# Build the plugin
uv run python build.py

# Install to Calibre
calibre-customize -a RanobeDB-Light-Novels.zip
```

## Configuration

After installation, configure the plugin:

1. Go to **Preferences** → **Plugins**
2. Find "RanobeDB Light Novels" under "Metadata download"
3. Click **Customize plugin**

### Options

| Option | Default | Description |
|--------|---------|-------------|
| Preferred Language | English | Language for titles (English, Japanese, Romaji) |
| Maximum Results | 10 | Number of search results to return (1-25) |

## Usage

### Downloading Metadata

1. Select one or more books in your Calibre library
2. Right-click and select **Edit metadata** → **Download metadata**
3. Or use the keyboard shortcut (default: `D`)
4. RanobeDB Light Novels will appear as one of the metadata sources

### Using RanobeDB ID

If you know the RanobeDB book ID:

1. Edit the book's metadata
2. Add an identifier: `ranobedb:12345` (replace with actual ID)
3. Download metadata - the plugin will do a direct lookup

### Finding RanobeDB IDs

The RanobeDB ID can be found in the URL of a book's page:
- `https://ranobedb.org/book/12345` → ID is `12345`

## API Information

This plugin uses the [RanobeDB API v0](https://ranobedb.org/api/docs/v0):

- **Rate Limit**: 60 requests per minute
- **License**: Data is under [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/1-0/)

The plugin automatically respects the rate limit by spacing requests at least 1 second apart.

## Troubleshooting

### No results found

- Try searching with just the title (without author)
- Check if the book exists on [RanobeDB](https://ranobedb.org)
- Try using the English title or the original Japanese title

### Covers not downloading

- Check your internet connection
- The book may not have a cover image on RanobeDB
- Try downloading metadata again

### Wrong metadata

- Configure the preferred language in plugin settings
- Use the RanobeDB ID for exact matches
- Report data issues on [RanobeDB Discord](https://discord.gg/ZeAnhGncFx)

## Development

### Project Structure

```
ranobedb-calibre-plugin/
├── pyproject.toml                              # UV project config
├── README.md                                   # This file
├── build.py                                    # Build script
├── build.sh                                    # Shell build script
└── src/
    └── ranobedb_light_novels/
        ├── __init__.py                         # Main plugin code
        └── plugin-import-name-ranobedb_light_novels.txt
```

### Building

```bash
# Using shell script
./build.sh

# Using Python
python build.py

# Using UV
uv run python build.py
```

### Testing

The plugin includes basic tests that can be run with Calibre's testing framework:

```bash
calibre-debug -e src/ranobedb_light_novels/__init__.py
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This plugin is licensed under the GPL v3 license, the same as Calibre.

## Credits

- [RanobeDB](https://ranobedb.org) - The database and API
- [Calibre](https://calibre-ebook.com) - The e-book management software

## Links

- [RanobeDB Website](https://ranobedb.org)
- [RanobeDB API Documentation](https://ranobedb.org/api/docs/v0)
- [RanobeDB Discord](https://discord.gg/ZeAnhGncFx)
- [Calibre Plugin Development](https://manual.calibre-ebook.com/creating_plugins.html)
