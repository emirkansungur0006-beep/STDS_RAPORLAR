import sys, os
sys.path.append(os.getcwd())
from reference_matcher import ReferenceMatcher, normalize_turkish, similarity_ratio

matcher = ReferenceMatcher()
test_name = "SÜREYYAPAŞA GÖĞÜS HASTALIKLARI VE GÖĞÜS CERRAHİSİ EĞİTİM VE ARAŞTIRMA HASTANESİ"
print(f"Testing match for: {test_name}")
match = matcher.match_by_name(test_name, threshold=0.5)
if match:
    print(f"MATCH FOUND: {match['kurum_adi']} (Score: {similarity_ratio(test_name, match['kurum_adi'])})")
else:
    print("NO MATCH FOUND")
    # Benzerleri listele
    print("Near matches:")
    for h in matcher.hospitals:
        score = similarity_ratio(test_name, h['kurum_adi'])
        if score > 0.4:
            print(f"  - {h['kurum_adi']} (Score: {score})")
