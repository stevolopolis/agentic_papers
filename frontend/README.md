# ArXiv Papers Viewer

A web-based dataset viewer for navigating through the SQLite database of arXiv papers.

## Features

- View papers in a paginated grid layout
- Search papers by title or abstract
- View detailed information about each paper
- Links to original papers and project pages (if available)
- Responsive design that works on desktop and mobile

## Prerequisites

- Python 3.7+
- SQLite database with arXiv papers (created by the main.py script)

## Installation

1. Clone this repository or navigate to the project directory
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Make sure your SQLite database (`arxiv_papers.db`) is in the parent directory
2. Run the Flask application:

```bash
python app.py
```

3. Open your web browser and navigate to `http://localhost:5000`

## Database Structure

The application expects a SQLite database with the following structure:

```sql
CREATE TABLE papers (
    id TEXT PRIMARY KEY,
    title TEXT,
    author_list TEXT,
    pub_venue TEXT,
    pub_lab TEXT,
    subjects TEXT,
    abstract TEXT,
    link_to_paper TEXT,
    link_to_project_page TEXT
)
```

## API Endpoints

- `GET /api/papers` - Get a paginated list of papers
  - Query parameters:
    - `page` - Page number (default: 1)
    - `per_page` - Number of papers per page (default: 10)
    - `search` - Search term for filtering papers by title or abstract
  
- `GET /api/paper/<paper_id>` - Get details of a specific paper by ID 