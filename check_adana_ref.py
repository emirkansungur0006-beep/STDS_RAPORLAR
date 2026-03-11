import sys, os
sys.path.append(os.getcwd())
from reference_matcher import ReferenceMatcher

matcher = ReferenceMatcher()
adana_hospitals = [h for h in matcher.reference_data if h['il'] == 'ADANA']
print(f"Adana Hospitals in Reference ({len(adana_hospitals)}):")
for h in adana_hospitals[:10]:
    print(f"- {h['kurum_adi']} ({h['kurum_kodu']})")
