import requests
import logging
import time
import csv
import json
import base64
from pathlib import Path

logger = logging.getLogger(__name__)

class MusicFetcher:
    BASE_URL = "https://itunes.apple.com/search"
    MB_WORK_URL = "https://musicbrainz.org/ws/2/work"

    WIKIPEDIA_SEARCH_URL = "https://api.wikimedia.org/core/v1/wikipedia/en/search/page"
    WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"

    SPOTIFY_AUTH_URL = "https://accounts.spotify.com/api/token"
    SPOTIFY_SEARCH_URL = "https://api.spotify.com/v1/search"

    def __init__(self):
        self.spotify_token = None
        self.spotify_token_expires = 0
        self._load_spotify_config()

    def _load_spotify_config(self):
        """Load Spotify API credentials from config file."""
        config_path = Path(__file__).parent / "spotify_config.json"
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.spotify_client_id = config.get("client_id", "")
                self.spotify_client_secret = config.get("client_secret", "")
                if not self.spotify_client_id or self.spotify_client_id == "YOUR_SPOTIFY_CLIENT_ID":
                    logger.warning("Spotify credentials not configured. Spotify lookup will be skipped.")
        except FileNotFoundError:
            logger.warning("spotify_config.json not found. Spotify lookup will be skipped.")
            self.spotify_client_id = ""
            self.spotify_client_secret = ""

    def _get_spotify_token(self):
        """Get Spotify API access token using client credentials flow."""
        if self.spotify_token and time.time() < self.spotify_token_expires:
            return self.spotify_token

        if not self.spotify_client_id or not self.spotify_client_secret:
            return None

        try:
            auth_str = f"{self.spotify_client_id}:{self.spotify_client_secret}"
            auth_b64 = base64.b64encode(auth_str.encode()).decode()

            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {"grant_type": "client_credentials"}

            response = requests.post(self.SPOTIFY_AUTH_URL, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()

            self.spotify_token = token_data["access_token"]
            self.spotify_token_expires = time.time() + token_data["expires_in"] - 60
            return self.spotify_token

        except Exception as e:
            logger.warning(f"Failed to get Spotify token: {e}")
            return None

    def fetch_spotify_metadata(self, query: str):
        """Search Spotify for a track and return track ID and URL."""
        token = self._get_spotify_token()
        if not token:
            return None

        try:
            headers = {"Authorization": f"Bearer {token}"}
            params = {
                "q": query,
                "type": "track",
                "limit": 1
            }

            response = requests.get(self.SPOTIFY_SEARCH_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            tracks = data.get("tracks", {}).get("items", [])
            if not tracks:
                logger.warning(f"No Spotify results for '{query}'")
                return None

            track = tracks[0]
            return {
                "id": track["id"],
                "url": track["external_urls"]["spotify"],
                "name": track["name"],
                "artists": ", ".join([artist["name"] for artist in track["artists"]]),
                "album": track["album"]["name"]
            }

        except Exception as e:
            logger.warning(f"Spotify lookup error for '{query}': {e}")
            return None

    def fetch_composition_year_from_wikidata(self, title: str, composer: str | None) -> str | None:
        """Best-effort lookup of a work's composition/publication year via Wikipedia/Wikidata.

        Strategy:
        - Use Wikimedia REST API to search Wikipedia for the work.
        - Extract Wikidata ID from the search results.
        - Fetch the Wikidata entity and read:
          - P571 (inception / composition) first
          - otherwise P577 (publication date)
        - Normalize to a 4-digit year string.
        """
        try:
            if not title:
                return None

            headers = {
                "User-Agent": "Flexster/0.1.0 (https://github.com/example/flexster; contact@example.com)",
                "Accept": "application/json"
            }

            # Build search query - include composer if available
            search_query = title
            if composer:
                # Try adding composer to improve matching
                search_query = f"{composer} {title}"

            params = {
                "q": search_query,
                "limit": 5
            }

            time.sleep(1.0)  # Rate limiting
            resp = requests.get(self.WIKIPEDIA_SEARCH_URL, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            pages = data.get("pages", [])
            if not pages:
                return None

            composer_lc = composer.lower() if composer else None

            # Score pages to find the best match
            def score_page(page: dict) -> int:
                score = 0
                desc = (page.get("description") or "").lower()
                title_text = (page.get("title") or "").lower()
                excerpt = (page.get("excerpt") or "").lower()
                
                # Prefer musical works
                if any(kw in desc for kw in ["opera", "symphony", "composition", "song", "album", "musical work"]):
                    score += 3
                if any(kw in excerpt for kw in ["composed", "composition", "written", "album"]):
                    score += 2
                    
                # Match composer name
                if composer_lc:
                    composer_parts = composer_lc.split()
                    for part in composer_parts:
                        if len(part) > 3:
                            if part in desc or part in title_text or part in excerpt:
                                score += 4
                return score

            pages_sorted = sorted(pages, key=score_page, reverse=True)
            best_page = pages_sorted[0] if pages_sorted else pages[0]

            # Get Wikidata ID from the page key
            page_key = best_page.get("key")
            if not page_key:
                return None

            # Fetch the Wikidata ID via Wikipedia API
            wikipedia_title = page_key.replace("_", " ")
            wikidata_url = f"https://en.wikipedia.org/w/api.php"
            wikidata_params = {
                "action": "query",
                "prop": "pageprops",
                "ppprop": "wikibase_item",
                "titles": wikipedia_title,
                "format": "json"
            }
            
            time.sleep(1.0)
            wikidata_resp = requests.get(wikidata_url, params=wikidata_params, headers=headers, timeout=10)
            wikidata_resp.raise_for_status()
            wikidata_data = wikidata_resp.json()

            pages_dict = wikidata_data.get("query", {}).get("pages", {})
            entity_id = None
            for page_id, page_data in pages_dict.items():
                entity_id = page_data.get("pageprops", {}).get("wikibase_item")
                if entity_id:
                    break

            if not entity_id:
                return None

            # Fetch entity data from Wikidata
            entity_url = self.WIKIDATA_ENTITY_URL.format(entity_id)
            time.sleep(1.0)
            entity_resp = requests.get(entity_url, headers=headers, timeout=10)
            entity_resp.raise_for_status()
            entity_data = entity_resp.json()

            entities = entity_data.get("entities", {})
            if entity_id not in entities:
                return None
            entity = entities[entity_id]
            claims = entity.get("claims", {})

            def extract_year(prop: str) -> str | None:
                snaks = claims.get(prop)
                if not snaks:
                    return None
                try:
                    # Take the first value
                    datavalue = snaks[0]["mainsnak"]["datavalue"]["value"]
                    time_str = datavalue["time"]  # e.g. "+1724-01-01T00:00:00Z"
                    year = time_str.lstrip("+").lstrip("-")[:4]
                    if year.isdigit():
                        return year
                except Exception:
                    return None
                return None

            # P571: inception (often composition date)
            year = extract_year("P571")
            if year:
                return year

            # P577: publication date
            year = extract_year("P577")
            return year

        except Exception as e:
            logger.warning(f"Wikipedia/Wikidata lookup error for '{title}': {e}")
            return None

    def fetch_work_details_from_mb(self, title: str, artist: str, original_query: str = None):
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
                
                composer_name = None
                work_year = None

                for relation in work_details.get("relations", []):
                    if relation.get("type") == "composer":
                        composer_name = relation["artist"]["name"]
                        break # Found composer
                
                # Try to find work year (composition date)
                # Check for 'begin' date in relations (e.g. premiere) or work attributes
                # Note: MusicBrainz Works often don't have a direct date, but let's check life-span if available
                # or look for a 'premiere' relation.
                
                # Check life-span for work creation date
                if not work_year:
                    life_span = work_details.get("life-span", {})
                    if life_span.get("begin"):
                        work_year = life_span["begin"][:4]

                for relation in work_details.get("relations", []):
                    if relation.get("type") == "performance":
                        # Check for premiere date
                        if "begin" in relation:
                            work_year = relation["begin"][:4]
                            break
                
                if not work_year:
                     # Fallback: check if there is a disambiguation that looks like a year? No, unreliable.
                     pass

                if composer_name:
                    return {"composer": composer_name, "year": work_year}
                        
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
                    
                    composer_name = None
                    for relation in work_details.get("relations", []):
                        if relation.get("type") == "composer":
                            composer_name = relation["artist"]["name"]
                            break
                    
                    if composer_name:
                        # Heuristic 1: Check if composer name matches iTunes artist
                        if artist and composer_name.lower() in artist.lower():
                            return {"composer": composer_name, "year": None}
                            
                        # Heuristic 2: Check if composer name is in original query
                        parts = composer_name.split()
                        for part in parts:
                            if len(part) > 3 and part.lower() in original_query.lower():
                                return {"composer": composer_name, "year": None}
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
            
            # Extract recording year from releaseDate (e.g., "2011-01-24T08:00:00Z")
            release_date = result.get("releaseDate", "")
            recording_year = release_date[:4] if release_date else "Unknown"

            title = result.get("trackName", "Unknown Title")
            artist = result.get("artistName", "Unknown Artist")
            
            composer = result.get("composer")

            # Always try MusicBrainz to verify classical works and get a composition year
            mb_data = self.fetch_work_details_from_mb(title, artist, original_query=query)

            final_composer = composer
            composition_year = None

            if mb_data:
                if not final_composer:
                    final_composer = mb_data.get("composer")

                # Prefer work/composition year from MusicBrainz when available
                if mb_data.get("year"):
                    composition_year = mb_data.get("year")

            # If we still have no composition_year, try Wikidata as a best-effort fallback
            if not composition_year:
                composition_year = self.fetch_composition_year_from_wikidata(title, final_composer or artist)

            # Fetch Spotify metadata only if credentials are configured
            spotify_link = ""
            if self.spotify_client_id and self.spotify_client_id != "YOUR_SPOTIFY_CLIENT_ID":
                logger.info(f"Looking up Spotify data for '{query}'...")
                spotify_data = self.fetch_spotify_metadata(query)
                spotify_link = spotify_data["url"] if spotify_data else ""

            return {
                "query": query,
                "title": title,
                "artist": artist,
                "composer": final_composer if final_composer else "Unknown Composer",
                "album": result.get("collectionName", "Unknown Album"),
                # "year" keeps backward compatibility but now prefers composition year
                "year": composition_year or recording_year,
                "recording_year": recording_year,
                "composition_year": composition_year or "",
                "genre": result.get("primaryGenreName", "Unknown Genre"),
                "apple_link": result.get("trackViewUrl", ""),
                "spotify_link": spotify_link
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
