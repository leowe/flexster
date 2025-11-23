import logging
import argparse
import sys
from music_fetcher import MusicFetcher
from pdf_generator import PDFGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate music flashcards with QR codes.")
    parser.add_argument(
        "--input", "-i", 
        type=str, 
        help="Path to a text file containing music titles (one per line). If not provided, uses a default list."
    )
    parser.add_argument(
        "--no-mirror", 
        action="store_true", 
        help="Disable mirroring of metadata on the back page (useful for single-sided printing)."
    )
    parser.add_argument(
        "--rows", "-r", 
        type=int, 
        default=4, 
        help="Number of rows of cards per page (default: 4)."
    )
    parser.add_argument(
        "--cols", "-c", 
        type=int, 
        default=3, 
        help="Number of columns of cards per page (default: 3)."
    )
    parser.add_argument(
        "--platform", "-p",
        type=str,
        choices=["apple", "spotify"],
        default="apple",
        help="Music platform for QR codes: 'apple' for Apple Music or 'spotify' for Spotify (default: apple)."
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="music_cards",
        help="Output filename prefix for CSV and PDF files (default: music_cards). Will generate <name>.csv and <name>.pdf"
    )
    return parser.parse_args()

def main():
    args = parse_arguments()

    # List of music titles to process
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                music_titles = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(music_titles)} titles from {args.input}")
        except IOError as e:
            logger.error(f"Error reading input file: {e}")
            sys.exit(1)
    else:
        music_titles = [
            "Handel Giulio Cesare",
            "A Love Supreme (Acknowledgment)",
            "Bohemian Rhapsody",
            "Kind of Blue So What",
            "Beethoven Symphony 9"
        ]
        logger.info("Using default music titles list.")

    fetcher = MusicFetcher()
    results = fetcher.fetch_all(music_titles)

    if results:
        # Save to CSV
        csv_filename = f"{args.output}.csv"
        fetcher.save_to_csv(results, filename=csv_filename)

        # Generate PDF
        logger.info("Generating PDF...")
        # Mirroring is True by default, so we pass False if --no-mirror is set
        mirror_metadata = not args.no_mirror
        
        pdf_filename = f"{args.output}.pdf"
        pdf_gen = PDFGenerator(
            pdf_filename, 
            mirror_metadata=mirror_metadata,
            rows=args.rows,
            cols=args.cols,
            platform=args.platform
        )
        pdf_gen.create_pdf(results)
        logger.info("PDF generation complete.")
    else:
        logger.warning("No results found. Exiting.")

if __name__ == '__main__':
    main()
