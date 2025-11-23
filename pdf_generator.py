from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import qrcode
import io
import logging

logger = logging.getLogger(__name__)

class PDFGenerator:
    def __init__(self, filename="music_cards.pdf", mirror_metadata=True, rows=4, cols=3, platform="apple"):
        self.filename = filename
        self.mirror_metadata = mirror_metadata
        self.rows = rows
        self.cols = cols
        self.platform = platform
        self.styles = getSampleStyleSheet()

    def generate_qr_image(self, data):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        return img_buffer

    def create_pdf(self, music_data_list):
        # Filter out None items
        items = [item for item in music_data_list if item]
        
        # Reduced margins to give more space
        margin = 10
        doc = SimpleDocTemplate(
            self.filename, 
            pagesize=A4,
            rightMargin=margin, leftMargin=margin, 
            topMargin=margin, bottomMargin=margin
        )
        elements = []
        
        # Grid settings
        COLS = self.cols
        ROWS = self.rows
        ITEMS_PER_PAGE = COLS * ROWS
        
        # Calculate cell dimensions
        page_width, page_height = A4
        avail_width = page_width - 2 * margin
        # Subtract a larger buffer to prevent table splitting across pages
        # The table needs to fit comfortably within the page body
        avail_height = page_height - 2 * margin - 30 
        
        col_width = avail_width / COLS
        row_height = avail_height / ROWS

        # Styles
        centered_style = ParagraphStyle(
            'Centered', 
            parent=self.styles['Normal'], 
            alignment=1, # Center
            fontSize=12, 
            leading=14,
        )

        # Process in chunks
        for i in range(0, len(items), ITEMS_PER_PAGE):
            chunk = items[i:i + ITEMS_PER_PAGE]
            
            # --- Front Page (QR Codes) ---
            front_data = []
            for r in range(ROWS):
                row_data = []
                for c in range(COLS):
                    idx = r * COLS + c
                    if idx < len(chunk):
                        item = chunk[idx]
                        # Select link based on platform
                        link_key = f"{self.platform}_link"
                        qr_link = item.get(link_key)
                        if not qr_link:
                            logger.warning(f"No {self.platform} link found for '{item.get('title', 'Unknown')}', skipping QR code")
                            row_data.append("")
                            continue
                        qr_buffer = self.generate_qr_image(qr_link)
                        # Scale QR code to fit nicely
                        qr_size = min(col_width, row_height) * 0.8
                        qr_img = Image(qr_buffer, width=qr_size, height=qr_size)
                        row_data.append(qr_img)
                    else:
                        row_data.append("")
                front_data.append(row_data)
            
            front_table = Table(front_data, colWidths=[col_width]*COLS, rowHeights=[row_height]*ROWS)
            front_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black), # Grid lines for cutting
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(front_table)
            elements.append(PageBreak())

            # --- Back Page (Metadata) ---
            back_data = []
            for r in range(ROWS):
                row_data = []
                
                # Determine column order based on mirroring setting
                if self.mirror_metadata:
                    col_range = range(COLS - 1, -1, -1)
                else:
                    col_range = range(COLS)

                for c in col_range:
                    idx = r * COLS + c
                    if idx < len(chunk):
                        item = chunk[idx]

                        composition_year = item.get('composition_year') or ""
                        recording_year = item.get('recording_year') or ""

                        # Build separate year lines - prefer earlier date as composition
                        if composition_year and recording_year:
                            # Use the earlier year as composition
                            try:
                                comp_int = int(composition_year)
                                rec_int = int(recording_year)
                                if comp_int > rec_int:
                                    # Swap if composition year is later
                                    composition_year, recording_year = recording_year, composition_year
                            except ValueError:
                                pass  # Keep as is if conversion fails
                        
                        if composition_year:
                            year_line = f"<b><font size=14>{composition_year}</font></b><br/>"
                            if recording_year and composition_year != recording_year:
                                year_line += f"<font size=8>(rec. {recording_year})</font><br/>"
                        else:
                            year_line = f"<b>{recording_year}</b><br/>"

                        metadata_text = f"""
                        <b>{item['title']}</b><br/><br/>
                        {year_line}
                        {item['artist']}<br/>
                        <i>{item['album']}</i><br/>
                        {item['composer']}<br/>
                        {item['genre']}
                        """
                        metadata_para = Paragraph(metadata_text, centered_style)
                        row_data.append(metadata_para)
                    else:
                        row_data.append("")
                back_data.append(row_data)

            back_table = Table(back_data, colWidths=[col_width]*COLS, rowHeights=[row_height]*ROWS)
            back_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 10), # Keep padding for text
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(back_table)
            elements.append(PageBreak())

        doc.build(elements)
