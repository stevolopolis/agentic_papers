from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

app = Flask(__name__)

# Get the path to the database file
DB_PATH = Path(__file__).parent.parent / "arxiv_papers.db"

def get_db_connection():
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

def find_closest_date(conn, target_date):
    """Find the closest date to the target date that has papers."""
    # First try to find the closest date by checking dates in both directions
    query = """
        SELECT date_published FROM papers 
        WHERE date_published IS NOT NULL AND date_published != ''
        GROUP BY date_published
        ORDER BY ABS(julianday(date_published) - julianday(?))
        LIMIT 1
    """
    closest_date = conn.execute(query, (target_date,)).fetchone()
    
    if closest_date:
        return closest_date[0]
    
    # If no date found, return the most recent date
    query = """
        SELECT date_published FROM papers 
        WHERE date_published IS NOT NULL AND date_published != ''
        GROUP BY date_published
        ORDER BY date_published DESC
        LIMIT 1
    """
    most_recent = conn.execute(query).fetchone()
    
    if most_recent:
        return most_recent[0]
    
    return None

@app.route('/api/papers')
def get_papers():
    """API endpoint to get papers with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    date = request.args.get('date', '', type=str)
    search_term = request.args.get('search', '', type=str)
    
    # If per_page is very large (e.g., 1000), treat it as "All"
    is_all = per_page >= 1000
    
    conn = get_db_connection()
    
    # Build the query based on whether there's a search term or date
    query_params = []
    closest_date = None
    
    if search_term:
        search_condition = "WHERE title LIKE ? OR abstract LIKE ?"
        query_params = [f'%{search_term}%', f'%{search_term}%']
    elif date:
        # First check if there are any papers with the requested date
        date_check_query = "SELECT COUNT(*) FROM papers WHERE date_published = ?"
        date_count = conn.execute(date_check_query, (date,)).fetchone()[0]
        
        if date_count > 0:
            # Use the requested date
            search_condition = "WHERE date_published = ?"
            query_params = [date]
        else:
            # Find the closest date that has papers
            closest_date = find_closest_date(conn, date)
            
            if closest_date:
                search_condition = "WHERE date_published = ?"
                query_params = [closest_date]
            else:
                search_condition = ""
    else:
        search_condition = ""
    
    # Get total count for pagination
    count_query = f"SELECT COUNT(*) FROM papers {search_condition}"
    total = conn.execute(count_query, query_params).fetchone()[0]
    
    # Get the papers for the current page
    if is_all:
        # If showing all, don't use LIMIT and OFFSET
        query = f"""
            SELECT * FROM papers 
            {search_condition}
            ORDER BY date_published DESC
        """
        papers = conn.execute(query, query_params).fetchall()
    else:
        # Normal pagination
        offset = (page - 1) * per_page
        query = f"""
            SELECT * FROM papers 
            {search_condition}
            ORDER BY date_published DESC
            LIMIT ? OFFSET ?
        """
        query_params.extend([per_page, offset])
        papers = conn.execute(query, query_params).fetchall()
    
    # Convert papers to list of dicts
    papers_list = []
    for paper in papers:
        paper_dict = dict(paper)
        # Parse author_list from JSON string if it's not None
        if paper_dict['author_list'] and paper_dict['author_list'] != 'None':
            try:
                paper_dict['author_list'] = json.loads(paper_dict['author_list'])
            except json.JSONDecodeError:
                paper_dict['author_list'] = paper_dict['author_list']
        papers_list.append(paper_dict)
    
    conn.close()
    
    response_data = {
        'papers': papers_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if not is_all else 1
    }
    
    # Include the closest date in the response if it was used
    if closest_date:
        response_data['closest_date'] = closest_date
    
    return jsonify(response_data)

@app.route('/api/paper/<paper_id>')
def get_paper(paper_id):
    """API endpoint to get a single paper by ID."""
    conn = get_db_connection()
    paper = conn.execute('SELECT * FROM papers WHERE id = ?', (paper_id,)).fetchone()
    conn.close()
    
    if paper is None:
        return jsonify({'error': 'Paper not found'}), 404
    
    paper_dict = dict(paper)
    # Parse author_list from JSON string if it's not None
    if paper_dict['author_list'] and paper_dict['author_list'] != 'None':
        try:
            paper_dict['author_list'] = json.loads(paper_dict['author_list'])
        except json.JSONDecodeError:
            paper_dict['author_list'] = paper_dict['author_list']
    
    return jsonify(paper_dict)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 