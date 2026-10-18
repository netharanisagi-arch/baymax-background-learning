#!/usr/bin/env python3
"""Baymax independent public encyclopedia research v7.

No external AI model or pretrained language model. Curated multidisciplinary
encyclopedia curriculum, 8 NEW articles per run, max 120 cached summaries.
This is retrieval knowledge, NOT model training. All output public.
"""
import datetime as dt
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'docs' / 'knowledge.json'
TOPICS = ROOT / 'topics.json'
CURRICULUM = [
  "Astronomy",
  "Solar System",
  "Earth",
  "Moon",
  "Sun",
  "Mercury (planet)",
  "Venus",
  "Mars",
  "Jupiter",
  "Saturn",
  "Uranus",
  "Neptune",
  "Star",
  "Galaxy",
  "Milky Way",
  "Black hole",
  "Universe",
  "Telescope",
  "Space exploration",
  "International Space Station",
  "Satellite",
  "Comet",
  "Asteroid",
  "Gravity",
  "Physics",
  "Energy",
  "Electricity",
  "Magnetism",
  "Light",
  "Sound",
  "Quantum mechanics",
  "Relativity",
  "Thermodynamics",
  "Chemistry",
  "Atom",
  "Molecule",
  "Chemical element",
  "Periodic table",
  "Oxygen",
  "Hydrogen",
  "Water",
  "Carbon",
  "Acid",
  "Base (chemistry)",
  "Photosynthesis",
  "Biology",
  "Cell (biology)",
  "DNA",
  "Genetics",
  "Evolution",
  "Ecology",
  "Ecosystem",
  "Biodiversity",
  "Climate",
  "Climate change",
  "Atmosphere of Earth",
  "Ocean",
  "River",
  "Mountain",
  "Volcano",
  "Earthquake",
  "Plate tectonics",
  "Continental drift",
  "Geography",
  "Map",
  "Continent",
  "Asia",
  "Africa",
  "Europe",
  "North America",
  "South America",
  "Antarctica",
  "Australia",
  "Sri Lanka",
  "Japan",
  "India",
  "China",
  "United States",
  "Brazil",
  "Egypt",
  "Kenya",
  "France",
  "Germany",
  "Singapore",
  "Indian Ocean",
  "Pacific Ocean",
  "World history",
  "Archaeology",
  "Ancient history",
  "Ancient Egypt",
  "Roman Empire",
  "Indus Valley Civilisation",
  "History of China",
  "History of Japan",
  "History of Sri Lanka",
  "Industrial Revolution",
  "Printing press",
  "Writing",
  "Alphabet",
  "Language",
  "Linguistics",
  "Sinhala language",
  "Japanese language",
  "English language",
  "Mathematics",
  "Arithmetic",
  "Algebra",
  "Geometry",
  "Trigonometry",
  "Calculus",
  "Statistics",
  "Probability",
  "Number",
  "Prime number",
  "Pi",
  "Computer",
  "Computing",
  "Computer science",
  "Algorithm",
  "Programming language",
  "Python (programming language)",
  "JavaScript",
  "Internet",
  "World Wide Web",
  "Computer network",
  "Cybersecurity",
  "Cryptography",
  "Artificial intelligence",
  "Machine learning",
  "Neural network (machine learning)",
  "Natural language processing",
  "Robotics",
  "Robot",
  "Electrical engineering",
  "Mechanical engineering",
  "Electronics",
  "Sensor",
  "Electric motor",
  "Renewable energy",
  "Solar power",
  "Wind power",
  "Hydroelectricity",
  "Battery (electricity)",
  "Transportation",
  "Train",
  "Rail transport",
  "Automobile",
  "Bicycle",
  "Aircraft",
  "Ship",
  "Agriculture",
  "Rice",
  "Tea",
  "Plant",
  "Tree",
  "Flower",
  "Botany",
  "Zoology",
  "Mammal",
  "Bird",
  "Fish",
  "Insect",
  "Bee",
  "Elephant",
  "Dolphin",
  "Whale",
  "Tiger",
  "Turtle",
  "Food",
  "Nutrition",
  "Human body",
  "Heart",
  "Lung",
  "Brain",
  "Nervous system",
  "Immune system",
  "Medicine",
  "Public health",
  "Hygiene",
  "Sports",
  "Football",
  "Cricket",
  "Olympic Games",
  "Music",
  "Musical instrument",
  "Visual arts",
  "Painting",
  "Photography",
  "Cinema",
  "Literature",
  "Poetry",
  "Architecture",
  "Philosophy",
  "Logic",
  "Education",
  "University",
  "Library",
  "Economics",
  "Currency",
  "Trade",
  "Democracy",
  "Constitution",
  "United Nations",
  "Human rights",
  "Culture",
  "Tradition",
  "Buddhist art",
  "Traditional music",
  "Time",
  "Calendar",
  "Measurement",
  "Metric system",
  "Scientific method",
  "Research",
  "Scientific theory",
  "Invention",
  "Innovation"
]
USER_AGENT = 'BaymaxOriginalBackgroundStudy/3.0 (https://github.com/netharanisagi-arch/baymax-background-learning)'
KEEP = 120
NEW_PER_RUN = 8

def read_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text('utf-8'))

def fetch_article(title, lang='en'):
    if lang not in ('en', 'si') or not isinstance(title, str) or not 2 <= len(title) <= 140:
        return None
    params = urlencode({'action':'query','format':'json','formatversion':2,
                        'prop':'extracts|info','exintro':1,'explaintext':1,
                        'inprop':'url','redirects':1,'titles':title})
    request = Request(f'https://{lang}.wikipedia.org/w/api.php?{params}',
                      headers={'User-Agent': USER_AGENT,'Accept':'application/json'})
    try:
        with urlopen(request, timeout=16) as resp:
            payload = json.loads(resp.read(300_000).decode('utf-8'))
    except HTTPError as e:
        # Do not bypass Wikimedia rate limits. Job will try again at the next scheduled run.
        if e.code == 429:
            raise RuntimeError('Wikipedia rate limit (429): waiting for next scheduled run') from e
        raise
    for page in payload.get('query', {}).get('pages', []):
        body = re.sub(r'\s+', ' ', str(page.get('extract') or '')).strip()
        source = str(page.get('fullurl') or '')
        parsed = urlparse(source)
        if (page.get('missing') or len(body)<85 or parsed.scheme!='https' or
                parsed.hostname!=f'{lang}.wikipedia.org' or not parsed.path.startswith('/wiki/')):
            continue
        return {'id': f'{lang}:{page["title"]}', 'title':str(page['title'])[:120],
                'summary':body[:700], 'source':source, 'lang':lang,
                'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}
    return None

def run():
    configured = read_json(TOPICS, [])
    if not isinstance(configured, list):
        raise ValueError('topics.json should be a list')
    candidates=[]
    # Rotation prioritizes existing owner topics, then spreads through general subjects.
    for row in configured:
        if isinstance(row,dict) and row.get('lang','en') in ('en','si') and isinstance(row.get('title'),str):
            candidates.append((row.get('lang','en'), row['title']))
    candidates.extend(('en',t) for t in CURRICULUM)
    seen=set();subjects=[]
    for lang,title in candidates:
        key=(lang,title.casefold())
        if key not in seen:
            subjects.append((lang,title));seen.add(key)
    existing=read_json(DATA, {'schema':1,'cursor':0,'items':[]})
    if existing.get('schema')!=1 or not isinstance(existing.get('items'),list):
        raise ValueError('Unknown knowledge.json schema; not overwriting')
    catalog={item['id']:item for item in existing['items'] if isinstance(item,dict) and isinstance(item.get('id'),str)}
    cursor=int(existing.get('cursor',0))%len(subjects)
    studied=0;fetched=0;visited=0
    # Skip already cached concepts where possible; retry missing at future cycles.
    while visited < len(subjects) and fetched < NEW_PER_RUN and studied < 15:
        lang,title=subjects[cursor]
        cursor=(cursor+1)%len(subjects);visited+=1
        if f'{lang}:{title}' in catalog: continue
        studied+=1
        try:
            item=fetch_article(title,lang)
            if item and item['id'] not in catalog:
                catalog[item['id']]=item;fetched+=1
                print('Read:',item['title'])
        except RuntimeError:
            break
        except Exception as exc:
            print('Could not read:',title,type(exc).__name__)
        time.sleep(0.45)
    # Keep a bounded, source-attributed public encyclopedia library.
    ordered=sorted(catalog.values(),key=lambda e:e.get('fetched_at',''))[-KEEP:]
    output={'schema':1,'cursor':cursor,'updated_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
            'items':ordered}
    DATA.parent.mkdir(parents=True,exist_ok=True)
    tmp=DATA.with_suffix('.tmp')
    tmp.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n','utf-8')
    tmp.replace(DATA)
    print(f'New articles: {fetched}. Knowledge Library: {len(ordered)}. This does NOT train a language model.')

if __name__=='__main__':run()
