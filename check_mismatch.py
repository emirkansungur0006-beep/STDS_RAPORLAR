
import psycopg2
from config import DB_CONFIG

def check():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("SELECT DISTINCT hastane_adi FROM gozlem_formlari")
    form_names = [r[0] for r in cur.fetchall()]
    
    cur.execute("SELECT DISTINCT hastane_adi FROM gozlem_gorselleri")
    gorsel_names = [r[0] for r in cur.fetchall()]
    
    print(f"Total Form Hospitals: {len(form_names)}")
    print(f"Total Gorsel Hospitals: {len(gorsel_names)}")
    
    def normalize(s):
        if not s: return ""
        return " ".join(s.strip().upper().split())

    matches = 0
    for g_name in gorsel_names:
        g1 = normalize(g_name)
        found = False
        for f_name in form_names:
            if g1 == normalize(f_name):
                matches += 1
                found = True
                print(f"MATCH: '{g_name}' == '{f_name}'")
                break
        if not found:
            # Try fuzzy match
            for f_name in form_names:
                f1 = normalize(f_name)
                if g1 in f1 or f1 in g1:
                    print(f"FUZZY: '{g_name}' ~ '{f_name}'")
                    break
            else:
                print(f"NO MATCH: '{g_name}'")

    cur.close()
    conn.close()

if __name__ == '__main__':
    check()
