import requests
import json
from urllib.parse import quote
import html
import time

def get_category_members(category_name, language='he'):
    """
    Fetch all pages from a Wikipedia category
    """
    members = []
    continue_token = None
    
    while True:
        # Prepare API parameters
        params = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': f'Category:{category_name}',
            'cmlimit': 'max',
            'format': 'json'
        }
        
        if continue_token:
            params['cmcontinue'] = continue_token
        
        # Make API request
        url = f'https://{language}.wikipedia.org/w/api.php'
        response = requests.get(url, params=params)
        data = response.json()
        
        # Extract members
        for member in data['query']['categorymembers']:
            if member['ns'] == 0:  # Only main namespace articles
                members.append({
                    'title': member['title'],
                    'pageid': member['pageid']
                })
        
        # Check if there are more results
        if 'continue' in data:
            continue_token = data['continue']['cmcontinue']
        else:
            break
    
    return members

def get_wikidata_id(page_title, language='he'):
    """
    Get Wikidata ID for a Wikipedia page
    """
    params = {
        'action': 'query',
        'prop': 'pageprops',
        'titles': page_title,
        'format': 'json'
    }
    
    url = f'https://{language}.wikipedia.org/w/api.php'
    response = requests.get(url, params=params)
    data = response.json()
    
    pages = data['query']['pages']
    for page_id, page_data in pages.items():
        if 'pageprops' in page_data and 'wikibase_item' in page_data['pageprops']:
            return page_data['pageprops']['wikibase_item']
    
    return None

def has_musicbrainz_id(wikidata_id):
    """
    Check if a Wikidata entity has a MusicBrainz artist ID (P434)
    """
    if not wikidata_id:
        return False
    
    params = {
        'action': 'wbgetentities',
        'ids': wikidata_id,
        'props': 'claims',
        'format': 'json'
    }
    
    url = 'https://www.wikidata.org/w/api.php'
    response = requests.get(url, params=params)
    data = response.json()
    
    if wikidata_id in data['entities']:
        entity = data['entities'][wikidata_id]
        if 'claims' in entity and 'P434' in entity['claims']:
            return True
    
    return False

def filter_artists_without_musicbrainz(artists, language='he'):
    """
    Filter artists to only those without MusicBrainz IDs
    """
    artists_without_mb = []
    total = len(artists)
    
    print(f"Checking {total} artists for MusicBrainz IDs...")
    
    for i, artist in enumerate(artists, 1):
        # Show progress
        if i % 10 == 0:
            print(f"Progress: {i}/{total} ({i/total*100:.1f}%)")
        
        try:
            # Get Wikidata ID
            wikidata_id = get_wikidata_id(artist['title'], language)
            
            if wikidata_id:
                # Check if has MusicBrainz ID
                if not has_musicbrainz_id(wikidata_id):
                    artists_without_mb.append({
                        'title': artist['title'],
                        'pageid': artist['pageid'],
                        'wikidata_id': wikidata_id
                    })
            else:
                # No Wikidata ID means no MusicBrainz ID
                artists_without_mb.append({
                    'title': artist['title'],
                    'pageid': artist['pageid'],
                    'wikidata_id': None
                })
            
            # Be nice to the APIs
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error checking {artist['title']}: {e}")
            # Include in results as we couldn't verify
            artists_without_mb.append({
                'title': artist['title'],
                'pageid': artist['pageid'],
                'wikidata_id': 'error'
            })
    
    return artists_without_mb

def generate_html(artists, category_name):
    """
    Generate an HTML page with artist links (only those without MusicBrainz)
    """
    html_content = f"""
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category_name} - אמנים ללא MusicBrainz</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }}
        .artist-table {{
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px;
            text-align: right;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #e74c3c;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #fff5f5;
        }}
        a {{
            text-decoration: none;
            color: #0366d6;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .musicbrainz-link {{
            color: #EB743B;
            font-weight: bold;
        }}
        .stats {{
            text-align: center;
            margin: 20px 0;
            color: #666;
        }}
        .wikidata-status {{
            font-size: 0.9em;
            color: #888;
        }}
        .no-wikidata {{
            color: #e74c3c;
        }}
    </style>
</head>
<body>
    <h1>{category_name}</h1>
    <div class="subtitle">אמנים שאין להם מזהה MusicBrainz בוויקינתונים</div>
    <div class="stats">נמצאו {len(artists)} אמנים ללא מזהה MusicBrainz</div>
    
    <table class="artist-table">
        <thead>
            <tr>
                <th>#</th>
                <th>שם האמן</th>
                <th>ויקיפדיה</th>
                <th>ויקינתונים</th>
                <th>הוסף ל-MusicBrainz</th>
            </tr>
        </thead>
        <tbody>
"""
    
    for i, artist in enumerate(artists, 1):
        artist_name = artist['title']
        wiki_url = f"https://he.wikipedia.org/wiki/{quote(artist_name)}"
        musicbrainz_url = f"https://musicbrainz.org/search?query={quote(artist_name)}&type=artist&method=indexed"
        
        # Wikidata status
        if artist['wikidata_id'] and artist['wikidata_id'] != 'error':
            wikidata_cell = f'<a href="https://www.wikidata.org/wiki/{artist["wikidata_id"]}" target="_blank">{artist["wikidata_id"]}</a>'
        elif artist['wikidata_id'] is None:
            wikidata_cell = '<span class="no-wikidata">אין מזהה</span>'
        else:
            wikidata_cell = '<span class="no-wikidata">שגיאה</span>'
        
        html_content += f"""
            <tr>
                <td>{i}</td>
                <td>{html.escape(artist_name)}</td>
                <td><a href="{wiki_url}" target="_blank">לדף ויקיפדיה</a></td>
                <td class="wikidata-status">{wikidata_cell}</td>
                <td><a href="{musicbrainz_url}" target="_blank" class="musicbrainz-link">חיפוש והוספה</a></td>
            </tr>
"""
    
    html_content += """
        </tbody>
    </table>
    
    <div style="margin-top: 40px; text-align: center; color: #666;">
        <p>אמנים אלו לא נמצאו עם מזהה MusicBrainz (P434) בוויקינתונים.</p>
        <p>ניתן לחפש אותם ב-MusicBrainz ולהוסיף את המזהה לוויקינתונים.</p>
    </div>
</body>
</html>
"""
    
    return html_content

def main():
    # You can change this to any category name
    category_name = "זמרים_ישראלים"  # Remove the "קטגוריה:" prefix
    
    print(f"Fetching artists from category: {category_name}")
    
    # Get all artists from the category
    all_artists = get_category_members(category_name)
    
    print(f"Found {len(all_artists)} total artists")
    
    # Filter to only those without MusicBrainz IDs
    artists_without_mb = filter_artists_without_musicbrainz(all_artists)
    
    print(f"\nFound {len(artists_without_mb)} artists without MusicBrainz IDs")
    
    # Sort artists alphabetically by Hebrew name
    artists_without_mb.sort(key=lambda x: x['title'])
    
    # Generate HTML
    html_content = generate_html(artists_without_mb, category_name)
    
    # Save to file
    output_filename = f"{category_name}_without_musicbrainz.html"
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nHTML file saved as: {output_filename}")
    
    # Print first few artists as a preview
    print("\nFirst 5 artists without MusicBrainz:")
    for artist in artists_without_mb[:5]:
        status = "No Wikidata" if artist['wikidata_id'] is None else artist['wikidata_id']
        print(f"- {artist['title']} (Wikidata: {status})")

if __name__ == "__main__":
    main()
