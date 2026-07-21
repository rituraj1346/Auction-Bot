# utils/pdf_generator.py
from fpdf import FPDF
import config

class AuctionSummaryPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "CONSOLIDATED UPCOMING AUCTIONS REPORT", ln=True, align="C")
        self.set_font("Arial", "I", 9)
        self.cell(0, 5, "Generated from MSTC Portal", ln=True, align="C")
        self.line(10, 27, 200, 27)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

def clean_text(text):
    if not text: return ""
    text = str(text)
    text = text.replace('•', '-').replace('₹', 'Rs.').replace('‘', "'").replace('’', "'")
    text = text.replace('“', '"').replace('”', '"').replace('–', '-').replace('—', '-')
    text = text.replace('\n', ' ') 
    
    words = text.split()
    safe_words = []
    for word in words:
        if len(word) > 75:
            safe_words.append(" ".join([word[i:i+75] for i in range(0, len(word), 75)]))
        else:
            safe_words.append(word)
    
    text = " ".join(safe_words)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def generate_summary(auctions):
    pdf = AuctionSummaryPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    epw = pdf.w - 20 
    
    for idx, item in enumerate(auctions, 1):
        
        title = clean_text(item.get('title', 'Unknown Title'))
        category = clean_text(item.get('category', 'General Scrap'))
        date = clean_text(item.get('date', 'Check Document'))
        materials = clean_text(item.get('materials', 'See details'))
        paperwork = clean_text(item.get('paperwork', 'Check terms'))
        location = clean_text(item.get('location', 'Region'))
        source = clean_text(item.get('source', 'MSTC'))
        
        pdf.set_x(10)
        pdf.set_font("Arial", "B", 11)
        pdf.multi_cell(epw, 6, f"{idx}. [{source.upper()}] {title}")
        
        pdf.set_x(10)
        pdf.set_font("Arial", "", 9)
        details = (
            f"    - Category       : {category}\n"
            f"    - Scheduled Date : {date}\n"
            f"    - Material Group : {materials}\n"
            f"    - EMD / Paperwork: {paperwork}\n"
            f"    - Lot Location   : {location}"
        )
        pdf.multi_cell(epw, 5, details)
        pdf.ln(6)
        
    pdf.output(config.OUTPUT_SUMMARY_PATH)
    return config.OUTPUT_SUMMARY_PATH