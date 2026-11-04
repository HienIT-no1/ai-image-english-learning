"""Build a reproducible 1,000-class LVIS dataset and a per-class data audit."""
from __future__ import annotations

import argparse
import ast
import collections
import csv
import hashlib
import json
import math
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from download import ROOT, download

# Deprioritize specialized/dated categories; preserve IDs and definitions from LVIS.
SPECIALIZED = set("""arctic armor bagpipe bait bass_horn bedpan beeper Bible pirate_flag
black_sheep blimp bob bolo_tie bonnet pipe_bowl bowler_hat brass_plaque breechcloth
broach horse_buggy horned_cow bulletproof_vest cabana cabin_car horse_carriage
chain_mail chalice chap poker_chip cigar_box cigarette_case clasp cleat cloak
coil coloring_material cornet cornice corset cougar coverall cowbell cream_pitcher
crossbar crouton crucifix crumb cub cylinder dagger dalmatian dress_hat dress_suit
electric_chair escargot eyepatch falcon fedora fighter_jet file flannel flap fleece
flipper foal freight_car futon gag gargoyle gasmask gazelle gemstone cincture
gondola gravy_boat grits grizzly gun hairnet halter_top ham handcuff harmonium
hatbox headstall heron home_plate hookah hornet houseboat hummingbird iPod jewel
keg kilt kimono knob knocker lamb-chop latch leather legume lightning_rod limousine
liquor loveseat machine_gun mail_slot mallard mallet mammoth manatee manger
martini mascot mast milestone milk_can mint_candy motor mound music_stool
neckerchief nosebag noseband nutcracker oil_lamp inkpad pad pan_(metal_container)
parakeet parasail parchment passenger_car passenger_ship patty wooden_leg pegboard
pelican pendulum pennant penny pew phonebook phonograph_record tobacco_pipe pistol
pitchfork plow plume pocket_watch poker pony projectile propeller prune puffer
puffin pug-dog quesadilla quiche radar raft ram reamer record_player reflector
rib rifle river_boat road_map rodent root_beer runner saddle saddle_blanket
saddlebag sail salmon_(fish) sawhorse scarecrow seabird seahorse seaplane shaker
sharpener Sharpie shepherd_dog sherbert shield shot_glass silo ski_parka skullcap
sombrero soupspoon soya_milk space_shuttle spear stagecoach stirrer stirrup strap
string_cheese subwoofer sweatband Tabasco_sauce tachometer army_tank tapestry
tartan tassel television_camera tequila thimble tiara tinsel cover trunk vat
turban turkey_(food) typewriter unicycle urinal urn videotape vodka vulture
wagon_wheel walrus water_scooter water_ski water_tower weathervane wedding_cake
wet_suit windmill window_box windsock wine_bucket blinder wristlet yacht yoke""".split())

# Explicit sense-preserving links, never fuzzy-match mouse to an animal.
LEGACY_IDS = {
    'keyboard':296, 'laptop':631, 'monitor':698, 'computer mouse':705,
    'apple':12, 'backpack':34, 'banana':45, 'bed':77, 'calculator':184,
    'chair':232, 'cherry':239, 'clock':271, 'coconut':283, 'sofa':982,
    'cucumber':342, 'dining table':367, 'eraser':425, 'grape':510,
    'kiwi':613, 'melon':684, 'microwave':687, 'notebook':724, 'orange':735,
    'oven':739, 'peach':774, 'pear':776, 'pen':781, 'pencil':782,
    'pineapple':806, 'refrigerator':421, 'ruler':681, 'scissors':923,
    'pencil sharpener':784, 'sink':961, 'strawberry':1025, 'table':1050,
    'toaster':1095, 'toilet':1097, 'television':1077, 'water bottle':1162,
    'watermelon':1172,
}
PROFILES = {'pilot': {'train':2, 'val':1, 'test':1}, 'full': {'train':100, 'val':15, 'test':10}}
_download_local=threading.local()


def download_image(url: str, target: Path) -> Path:
    """Reuse one HTTP connection pool per worker when fetching many small images."""
    if target.is_file() and target.stat().st_size:
        return target
    import requests
    if not hasattr(_download_local,'session'):
        _download_local.session=requests.Session()
    target.parent.mkdir(parents=True,exist_ok=True)
    partial=target.with_suffix('.jpg.part')
    for attempt in range(4):
        try:
            with _download_local.session.get(url,stream=True,timeout=(15,60)) as response:
                response.raise_for_status()
                expected=int(response.headers.get('Content-Length',0))
                received=0
                with partial.open('wb') as output:
                    for block in response.iter_content(128*1024):
                        output.write(block)
                        received+=len(block)
                if expected and expected!=received:
                    raise IOError('Incomplete image download')
            partial.replace(target)
            return target
        except (requests.RequestException,OSError):
            if attempt==3:
                raise
            time.sleep(2**attempt)
    raise AssertionError('unreachable')


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def load_annotations(split: str) -> dict:
    return json.loads((ROOT / f'data/raw/lvis_v1_{split}.json').read_text(encoding='utf-8'))


def normal(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()


def build_catalog(categories: list[dict], annotations: list[dict]) -> dict:
    counts = collections.Counter(a['category_id'] for a in annotations)
    protected = set(LEGACY_IDS.values())
    ranked = sorted(categories, key=lambda c: (
        c['id'] not in protected, c['name'] in SPECIALIZED,
        {'f':0, 'c':1, 'r':2}.get(c.get('frequency'), 3),
        -min(counts[c['id']], 2000), c['id']))
    selected = sorted(ranked[:1000], key=lambda c:c['id'])
    oi_rows = list(csv.reader((ROOT / 'data/raw/open_images_boxable.csv').open(encoding='utf-8')))
    oi_index = collections.defaultdict(list)
    for mid, name in oi_rows:
        oi_index[normal(name)].append({'id':mid, 'label':name})
    reverse_legacy = {value:key for key,value in LEGACY_IDS.items()}
    labels = []
    for index, cat in enumerate(selected):
        # Use the category's own sense-qualified name; generic aliases can be ambiguous.
        display = reverse_legacy.get(cat['id'], cat['name'].replace('_', ' '))
        oi_matches = []
        for mid in oi_index.get(normal(display), []):
            oi_matches.append({**mid, 'relation':'candidate_exact_name', 'reviewed':False})
        labels.append({'class_id':index, 'concept_key':f"lvis:{cat['id']}",
            'english':display, 'definition':cat.get('def', ''), 'aliases':cat.get('synonyms', []),
            'lvis_category_id':cat['id'], 'lvis_name':cat['name'],
            'lvis_frequency':cat.get('frequency'), 'source_box_count':counts[cat['id']],
            'priority':'legacy' if cat['id'] in protected else 'expansion',
            'everyday_review':'needed' if cat['name'] in SPECIALIZED or cat.get('frequency')=='r' else 'candidate',
            'open_images':oi_matches})
    source = ast.parse((ROOT.parent / 'backend/app/services/ai_service.py').read_text(encoding='utf-8-sig'))
    old = next(ast.literal_eval(n.value) for n in source.body if isinstance(n, ast.AnnAssign)
               and isinstance(n.target, ast.Name) and n.target.id=='LABEL_METADATA')
    legacy = []
    for canonical in dict.fromkeys(value[0] for value in old.values()):
        cid = LEGACY_IDS.get(canonical)
        legacy.append({'english':canonical, 'lvis_category_id':cid,
            'status':'exact_sense' if cid else 'needs_additional_data_or_sense_review',
            'old_labels':[k for k,v in old.items() if v[0]==canonical]})
    return {'schema_version':1, 'status':'initial_data_backed_catalog; everyday suitability still needs review',
        'label_count':len(labels), 'labels':labels, 'legacy_coverage':legacy,
        'sources':['https://www.lvisdataset.org/', 'https://storage.googleapis.com/openimages/web/index.html'],
        'notes':['Open Images name matches are candidates, not approved annotation mappings.',
                 'Class IDs are model IDs; never reuse them as database vocabulary_id.',
                 'No claim of reliable recognition follows merely from having 1000 classes.']}


def select_images(images: list[dict], annotations: list[dict], selected: set[int], quotas: dict,
                  source_split: str) -> dict[str, list[dict]]:
    by_image = collections.defaultdict(list)
    for ann in annotations:
        if ann['category_id'] in selected:
            by_image[ann['image_id']].append(ann)
    pools = collections.defaultdict(list)
    image_map = {image['id']:image for image in images}
    for iid, anns in by_image.items():
        split = 'train' if source_split=='train' else ('test' if int(hashlib.sha256(str(iid).encode()).hexdigest()[:8],16)%5==0 else 'val')
        pools[split].append(iid)
    result = {}
    for split, ids in pools.items():
        inverted = collections.defaultdict(list)
        for iid in sorted(ids):
            for cid in {a['category_id'] for a in by_image[iid]}:
                inverted[cid].append(iid)
        rng = random.Random(42)
        for group in inverted.values():
            rng.shuffle(group)
        chosen, counts = set(), collections.Counter()
        for cid in sorted(selected, key=lambda cid:(len(inverted[cid]), cid)):
            for iid in inverted[cid]:
                if counts[cid] >= quotas[split]:
                    break
                if iid not in chosen:
                    chosen.add(iid)
                    counts.update({a['category_id'] for a in by_image[iid]})
        result[split] = []
        for iid in sorted(chosen):
            image = image_map[iid]
            url = image.get('coco_url') or image.get('url')
            if not url or not re.match(r'^https?://images\.cocodataset\.org/(train2017|val2017)/[0-9]+\.jpg$',url):
                raise ValueError(f'Unexpected official image URL: {url}')
            # Positive classes are exhaustive only if not listed as non-exhaustive.
            positives = {a['category_id'] for a in by_image[iid]}
            verified = (set(image.get('neg_category_ids', [])) | (positives-set(image.get('not_exhaustive_category_ids', [])))) & selected
            result[split].append({'image_id':iid, 'width':image['width'], 'height':image['height'],
                'source_url':url, 'license':image.get('license'),
                'verified_categories':sorted(verified),
                'not_exhaustive_category_ids':image.get('not_exhaustive_category_ids', []),
                'annotations':[{'category_id':a['category_id'], 'bbox':a['bbox']} for a in by_image[iid]]})
    return result


def xywh_to_yolo(box: list, width: int, height: int) -> tuple:
    x,y,w,h = box
    if not all(math.isfinite(v) for v in (x,y,w,h,width,height)) or width<=0 or height<=0 or w<=0 or h<=0:
        raise ValueError('Invalid image or bounding box dimensions')
    x1,y1=max(0.0,x),max(0.0,y)
    x2,y2=min(float(width),x+w),min(float(height),y+h)
    if x2<=x1 or y2<=y1:
        raise ValueError('Bounding box lies outside image')
    return ((x1+x2)/2/width,(y1+y2)/2/height,(x2-x1)/width,(y2-y1)/height)


def materialize(root: Path, manifest: dict, workers: int) -> None:
    from PIL import Image
    records = [(split, record) for split,records in manifest['splits'].items() for record in records]
    def fetch(item):
        split, record = item
        cache = ROOT / 'data/images' / Path(record['source_url']).name
        path = download_image(record['source_url'], cache)
        with Image.open(path) as photo:
            photo.verify()
        with Image.open(path) as photo:
            if photo.size != (record['width'],record['height']):
                raise ValueError(f'Image dimensions differ: {path}')
        folder=root/'images'/split
        folder.mkdir(parents=True,exist_ok=True)
        target=folder/path.name
        if not target.exists():
            import os, shutil
            try: os.link(path,target)
            except OSError: shutil.copy2(path,target)
        with path.open('rb') as stream:
            return split,record['image_id'],hashlib.file_digest(stream,'sha256').hexdigest()
    hashes,failed={},[]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures={executor.submit(fetch,item):item for item in records}
        for number,future in enumerate(as_completed(futures),1):
            try:
                split,iid,digest=future.result()
                if digest in hashes and hashes[digest]['split'] != split:
                    failed.append({'image_id':iid,'error':'Duplicate image content across splits', 'other':hashes[digest]})
                hashes[digest]={'split':split,'image_id':iid}
            except Exception as exc:
                failed.append({'image_id':futures[future][1]['image_id'],'error':str(exc)})
            if number%100==0 or number==len(records):
                print(json.dumps({'downloaded':number,'total':len(records),'failed':len(failed)}),flush=True)
    save_json(root/'download_audit.json',{'images':len(records),'failures':failed,'sha256':hashes})
    if failed:
        raise RuntimeError(f'{len(failed)} failed/duplicate images; see download_audit.json; training blocked')
    (root/'READY').write_text(hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),encoding='utf-8')


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=PROFILES,default='pilot')
    parser.add_argument('--images',action='store_true')
    parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args()
    if args.workers<1 or args.workers>16:
        parser.error('workers must be in 1..16')
    root=ROOT/'data/prepared'/args.profile
    manifest_path=root/'manifest.json'
    if not manifest_path.exists():
        train=load_annotations('train')
        catalog=build_catalog(train['categories'],train['annotations'])
        save_json(ROOT/'catalog.json',catalog)
        selected={label['lvis_category_id'] for label in catalog['labels']}
        splits=select_images(train['images'],train['annotations'],selected,PROFILES[args.profile],'train')
        del train
        val=load_annotations('val')
        splits.update(select_images(val['images'],val['annotations'],selected,PROFILES[args.profile],'val'))
        del val
        manifest={'profile':args.profile,'seed':42,'classes':catalog['labels'],'splits':splits,
            'catalog_sha256':hashlib.sha256((ROOT/'catalog.json').read_bytes()).hexdigest(),
            'annotation_policy':'verified classes + assigned positive anchors only; unknown categories ignored'}
        save_json(manifest_path,manifest)
    else:
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    cid_map={label['lvis_category_id']:label['class_id'] for label in manifest['classes']}
    support={split:collections.Counter() for split in manifest['splits']}
    for split,records in manifest['splits'].items():
        folder=root/'labels'/split
        folder.mkdir(parents=True,exist_ok=True)
        for record in records:
            lines=[]
            for ann in record['annotations']:
                box=xywh_to_yolo(ann['bbox'],record['width'],record['height'])
                index=cid_map[ann['category_id']]
                lines.append(f"{index} "+' '.join(f'{v:.8f}' for v in box))
                support[split][index]+=1
            (folder/Path(record['source_url']).with_suffix('.txt').name).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # JSON is valid YAML; avoid executable download blocks and implicit downloads.
    data={'path':str(root.resolve()),'train':'images/train','val':'images/val','test':'images/test',
          'names':{label['class_id']:label['english'] for label in manifest['classes']}}
    save_json(root/'data.yaml',data)
    report={'label_count':len(cid_map),'image_counts':{s:len(r) for s,r in manifest['splits'].items()},
        'per_class':[{'class_id':label['class_id'],'english':label['english'],
            **{s+'_boxes':counts[label['class_id']] for s,counts in support.items()}} for label in manifest['classes']],
        'legacy_missing':[r for r in json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))['legacy_coverage'] if r['lvis_category_id'] is None],
        'status':'data preparation only; no quality claim'}
    save_json(root/'coverage.json',report)
    print(json.dumps({'label_count':len(cid_map),'images':report['image_counts'],
        'zero_train_support':sum(support['train'][i]==0 for i in cid_map.values()),
        'legacy_needing_more_data':report['legacy_missing']},ensure_ascii=False,indent=2),flush=True)
    if args.images:
        materialize(root,manifest,args.workers)


if __name__=='__main__':
    main()
