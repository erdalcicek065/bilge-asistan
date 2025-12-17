import os
import json
import re
from docx import Document

# ---------------------------------------------------------
# 📂 BURAYI KONTROL ET: Word dosyaların nerede?
# Eğer klasör ismin farklıysa burayı düzeltmelisin.
ROOT_FOLDER = "C:/Users/erdlc/Desktop/Kazanım Klasörü/Okul Öncesi" 
# ---------------------------------------------------------

# Çıktı nereye gidecek? (Otomatik data klasörüne)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(BASE_DIR, 'data', 'mufredat.json')

# Kategori Eşleştirmeleri (Word dosya isminde ne geçiyor -> Sisteme ne kaydedilsin)
CATEGORY_MAP = {
    "Alıcı Dil": "Alıcı Dil",
    "İfade Edici Dil": "İfade Edici Dil",
    "Bilişsel": "Bilişsel",
    "İnce Motor": "İnce Motor",
    "Kaba Motor": "Kaba Motor",
    "Sosyal": "Sosyal Duygusal",
    "Duygusal": "Sosyal Duygusal",
    "Uyum": "Uyumsal Beceriler",
    "Uyumsal": "Uyumsal Beceriler"
}

FINAL_DATA = {v: {} for v in set(CATEGORY_MAP.values())}

def clean_text(text):
    if not text: return None
    line = text.strip()
    if len(line) < 5: return None
    if line.replace('.', '').isdigit(): return None # Sadece sayıysa atla
    line = re.sub(r'^[\d\.\-\*\•\)\s]+', '', line) # Madde işaretlerini temizle
    if len(line) > 0: line = line[0].upper() + line[1:]
    return line

def extract_age_from_filename(filename):
    # Dosya isminden yaş grubunu bul (Örn: 0-3 Ay)
    match = re.search(r'(\d+-\d+(\s*Ay)?)', filename, re.IGNORECASE)
    if match: return match.group(0)
    return "Genel"

def main():
    print("🚀 Madenci Çalışıyor...")
    print(f"📂 Okunan Klasör: {ROOT_FOLDER}")

    if not os.path.exists(ROOT_FOLDER):
        print(f"❌ HATA: '{ROOT_FOLDER}' klasörü bulunamadı!")
        print("Lütfen koddaki ROOT_FOLDER satırını kontrol et.")
        return

    # Data klasörü yoksa oluştur
    if not os.path.exists(os.path.dirname(OUTPUT_PATH)):
        os.makedirs(os.path.dirname(OUTPUT_PATH))

    count = 0
    file_count = 0
    
    for root, dirs, files in os.walk(ROOT_FOLDER):
        for file in files:
            if file.lower().endswith(".docx") and not file.startswith("~$"):
                path = os.path.join(root, file)
                
                # Hangi kategori?
                cat = None
                for k, v in CATEGORY_MAP.items():
                    if k.lower() in file.lower(): 
                        cat = v
                        break
                
                if cat:
                    file_count += 1
                    age = extract_age_from_filename(file)
                    if age not in FINAL_DATA[cat]: FINAL_DATA[cat][age] = []
                    
                    try:
                        doc = Document(path)
                        added_local = 0
                        # Sadece tabloları oku
                        for table in doc.tables:
                            for row in table.rows:
                                for cell in row.cells:
                                    txt = clean_text(cell.text)
                                    # Mükerrer kayıt engelleme
                                    if txt and txt not in FINAL_DATA[cat][age]:
                                        FINAL_DATA[cat][age].append(txt)
                                        count += 1
                                        added_local += 1
                        print(f"   ✅ Okundu: {file} -> {cat} ({added_local} madde)")
                    except Exception as e:
                        print(f"   ⚠️ Hata ({file}): {e}")

    # JSON Olarak Kaydet
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(FINAL_DATA, f, ensure_ascii=False, indent=2)
    
    print("-" * 30)
    print(f"🎉 İŞLEM TAMAMLANDI!")
    print(f"Toplam {file_count} dosya tarandı.")
    print(f"Toplam {count} kazanım maddesi sisteme eklendi.")
    print(f"Dosya şuraya kaydedildi: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()