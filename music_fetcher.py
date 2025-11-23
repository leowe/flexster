import requests
import logging
import time
import csv

logger = logging.getLogger(__name__)

class MusicFetcher:
    BASE_URL = "https://itunes.apple.com/search"
    MB_WORK_URL = "https://musicbrainz.org/ws/2/work"

    def fetch_composer_from_mb(self, title: str, artist: str, original_query: str = None):
        headers = {"User-Agent": "Flexster/0.1.0 ( contact@example.com )"}
        
        # Prepare artist query (handle multiple artists)
        # iTunes: "Raphaël Pichon, Pygmalion & Sabine Devieilhe"
        # Split by , and &
        import re
        artists = re.split(r'[,&]', artist)
        artists = [a.strip().replace('"', '') for a in artists if a.strip()]
        
        # Construct artist part of query: artist:("A" OR "B")
        if artists:
            artist_query = ' OR '.join([f'"{a}"' for a in artists])
            artist_query = f'artist:({artist_query})'
        else:
            artist_query = ""
        
        # Prepare title variants
        title_variants = []
        clean_title = title.replace('"', '')
        title_variants.append(clean_title)
        
        # Variant: Remove "Composer: " prefix or "Series: " prefix
        if ": " in clean_title:
            parts = clean_title.split(": ", 1)
            if len(parts) > 1:
                title_variants.append(parts[1]) # "Giulio Cesare..."
                
        # Variant: Remove text in brackets
        base_title = re.sub(r'\(.*?\)', '', clean_title).strip()
        if base_title and base_title != clean_title:
            title_variants.append(base_title)

        # Try each title variant
        for t_variant in title_variants:
            if not artist_query:
                break
            query = f'recording:"{t_variant}" AND {artist_query}'
            
            try:
                time.sleep(1.2)
                response = requests.get("https://musicbrainz.org/ws/2/recording", params={"query": query, "fmt": "json", "limit": 1}, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if not data.get("recordings"):
                    continue # Try next variant
                
                recording = data["recordings"][0]
                recording_id = recording["id"]
                
                # Fetch recording details
                time.sleep(1.2)
                details_url = f"https://musicbrainz.org/ws/2/recording/{recording_id}"
                details_params = {"inc": "work-rels", "fmt": "json"}
                
                response = requests.get(details_url, params=details_params, headers=headers)
                response.raise_for_status()
                rec_details = response.json()
                
                work_id = None
                for relation in rec_details.get("relations", []):
                    if relation.get("target-type") == "work":
                        work_id = relation["work"]["id"]
                        break
                
                if not work_id:
                    continue
                    
                # Fetch work details
                time.sleep(1.2)
                work_url = f"https://musicbrainz.org/ws/2/work/{work_id}"
                work_params = {"inc": "artist-rels", "fmt": "json"}
                
                response = requests.get(work_url, params=work_params, headers=headers)
                response.raise_for_status()
                work_details = response.json()
                
                for relation in work_details.get("relations", []):
                    if relation.get("type") == "composer":
                        return relation["artist"]["name"]
                        
            except Exception as e:
                logger.warning(f"MB lookup error: {e}")
                continue
        
        # Fallback: Search for Work using original_query
        if original_query:
            try:
                time.sleep(1.2)
                # Search for work
                response = requests.get("https://musicbrainz.org/ws/2/work", params={"query": original_query, "fmt": "json", "limit": 3}, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for work in data.get("works", []):
                    work_id = work["id"]
                    # Fetch details
                    time.sleep(1.2)
                    work_url = f"https://musicbrainz.org/ws/2/work/{work_id}"
                    work_params = {"inc": "artist-rels", "fmt": "json"}
                    response = requests.get(work_url, params=work_params, headers=headers)
                    work_details = response.json()
                    
                    for relation in work_details.get("relations", []):
                        if relation.get("type") == "composer":
                            composer_name = relation["artist"]["name"]
                            
                            # Heuristic 1: Check if composer name matches iTunes artist
                            # (e.g. John Coltrane == John Coltrane)
                            if artist and composer_name.lower() in artist.lower():
                                return composer_name
                                
                            # Heuristic 2: Check if composer name is in original query
                            # (e.g. "Handel" in "Handel Giulio Cesare")
                            parts = composer_name.split()
                            for part in parts:
                                if len(part) > 3 and part.lower() in original_query.lower():
                                    return composer_name
            except Exception as e:
                logger.warning(f"Fallback MB lookup error: {e}")
                
        return None

    def fetch_metadata(self, query: str):
        params = {
            "term": query,
            "media": "music",
            "limit": 1
        }
        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data["resultCount"] == 0:
                logger.warning(f"No results found for '{query}'")
                return None
            
            result = data["results"][0]
            
            # Extract year from releaseDate (e.g., "2011-01-24T08:00:00Z")
            release_date = result.get("releaseDate", "")
            year = release_date[:4] if release_date else "Unknown"

            title = result.get("trackName", "Unknown Title")
            artist = result.get("artistName", "Unknown Artist")
            
            composer = result.get("composer")
            if not composer:
                logger.info(f"Composer not found in iTunes, querying MusicBrainz for '{title}' by '{artist}'...")
                composer = self.fetch_composer_from_mb(title, artist, original_query=query)

            return {
                "query": query,
                "title": title,
                "artist": artist,
                "composer": composer if composer else "Unknown Composer",
                "album": result.get("collectionName", "Unknown Album"),
                "year": year,
                "genre": result.get("primaryGenreName", "Unknown Genre"),
                "link": result.get("trackViewUrl", "")
            }
            
        except requests.RequestException as e:
            logger.error(f"Error fetching data for '{query}': {e}")
            return None

    def fetch_all(self, music_titles: list[str]) -> list[dict]:
        results = []
        logger.info("Starting music metadata fetch...")
        for title in music_titles:
            logger.info(f"Processing: {title}")
            data = self.fetch_metadata(title)
            if data:
                results.append(data)
            else:
                logger.warning(f"Could not find data for: {title}")
        return results

    def save_to_csv(self, data_list, filename="music_data.csv"):
        if not data_list:
            logger.warning("No data to save to CSV.")
            return

        keys = data_list[0].keys()
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as output_file:
                dict_writer = csv.DictWriter(output_file, fieldnames=keys)
                dict_writer.writeheader()
                dict_writer.writerows(data_list)
            logger.info(f"Data saved to {filename}")
        except IOError as e:
            logger.error(f"Error saving CSV: {e}")
