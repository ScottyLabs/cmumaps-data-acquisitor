# cmumaps-data-acquisitor

## Getting Started

### Prerequisites

- Git

- pip

- Permissions

- Get permission to view vault through (https://secrets.scottylabs.org/ui/vault/auth?with=oidc)

### Installation

1. Clone `cmumaps-data-acquisitor` from the GitHub by running `git clone https://github.com/ScottyLabs/cmumaps-data-acquisitor.git`.

2. Run `pip install -r requirements.txt` (this includes `minio`)

### Set up environment variables

1. Run `bun run vault:setup`

2. Run `bun run vault:pull`

### Running the Code

1. Run `svg_to_geojson_final.py`

2. Run `html_room_to_roomtype.py`

3. Run `geojson_to_json.py`
