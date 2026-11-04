"""Official LVIS box evaluation with class support and legacy-model comparison."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import time
from pathlib import Path

from download import ROOT
from prepare import LEGACY_IDS, normal, save_json


def official_evaluation(annotation_path: Path, detections: list, image_ids: set, category_ids: set):
    import numpy as np
    from lvis import LVIS, LVISResults, LVISEval
    truth=LVIS(str(annotation_path))
    predictions=LVISResults(truth,detections,max_dets=300)
    evaluator=LVISEval(truth,predictions,iou_type='bbox')
    evaluator.params.img_ids=sorted(image_ids)
    evaluator.params.cat_ids=sorted(category_ids)
    # lvis 0.5.3 predates NumPy 1.24; its accumulator still calls np.float.
    previous=np.__dict__.get('float')
    if previous is None:
        np.__dict__['float']=float
    try:
        evaluator.run()
    finally:
        if previous is None:
            np.__dict__.pop('float',None)
    return evaluator


def category_mapping(model_names: dict, labels: list[dict]) -> dict:
    exact={normal(label['english']):label['lvis_category_id'] for label in labels}
    source=ast.parse((ROOT.parent/'backend/app/services/ai_service.py').read_text(encoding='utf-8-sig'))
    old=next(ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.AnnAssign)
             and isinstance(n.target,ast.Name) and n.target.id=='LABEL_METADATA')
    result={}
    selected={label['lvis_category_id'] for label in labels}
    for key,name in model_names.items():
        canonical=old.get(name.lower(),(name,None,None))[0]
        category=exact.get(normal(name)) or LEGACY_IDS.get(canonical)
        if category in selected:
            result[int(key)]=category
    return result


def predict_individually(model, image_paths: list[str], **options):
    # Ultralytics treats a Python list as one LoadPilAndNumpy batch even when
    # batch=1 is specified. A file at a time keeps 1,000-class inference bounded.
    for path in image_paths:
        yield from model.predict(source=path,stream=True,batch=1,**options)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--profile',choices=['pilot','full'],default='pilot')
    parser.add_argument('--split',choices=['val','test'],default='val')
    parser.add_argument('--imgsz',type=int,default=640)
    parser.add_argument('--device',default='0')
    parser.add_argument('--name',required=True)
    args=parser.parse_args()
    import numpy as np
    from ultralytics import YOLO
    from train import validate_dataset
    root=ROOT/'data/prepared'/args.profile
    manifest=validate_dataset(root)
    output=ROOT/'reports'/args.name
    if (output/'summary.json').exists() and (output/'per_class.json').exists():
        raise RuntimeError('Report already exists; select a new --name')
    output.mkdir(parents=True,exist_ok=True)
    records=manifest['splits'][args.split]
    ids={record['image_id'] for record in records}
    categories={label['lvis_category_id'] for label in manifest['classes']}
    raw=json.loads((ROOT/'data/raw/lvis_v1_val.json').read_text(encoding='utf-8'))
    gt={key:value for key,value in raw.items() if key not in ('images','annotations','categories')}
    gt['images']=[im for im in raw['images'] if im['id'] in ids]
    gt['annotations']=[ann for ann in raw['annotations'] if ann['image_id'] in ids and ann['category_id'] in categories]
    gt['categories']=[cat for cat in raw['categories'] if cat['id'] in categories]
    del raw
    save_json(output/'ground_truth.json',gt)
    model=YOLO(str(args.model.resolve()))
    mapping=category_mapping(model.names,manifest['classes'])
    images=[str(root/'images'/args.split/Path(record['source_url']).name) for record in records]
    image_ids={Path(record['source_url']).name:record['image_id'] for record in records}
    detections=[]
    started=time.perf_counter()
    for index,result in enumerate(predict_individually(model,images,imgsz=args.imgsz,
                         device=args.device,conf=.001,max_det=300,verbose=False),1):
        iid=image_ids[Path(result.path).name]
        for xyxy,conf,cls in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist(),result.boxes.cls.cpu().tolist()):
            if int(cls) not in mapping:
                continue
            x1,y1,x2,y2=xyxy
            detections.append({'image_id':iid,'category_id':mapping[int(cls)],
                               'bbox':[x1,y1,x2-x1,y2-y1],'score':conf})
        if index%100==0:
            print(f'Evaluated {index}/{len(images)} images',flush=True)
    elapsed=time.perf_counter()-started
    save_json(output/'predictions.json',detections)
    if not detections:
        save_json(output/'summary.json',{'state':'no_mapped_detections','image_count':len(images),'model':str(args.model)})
        raise RuntimeError('No mapped predictions; no valid AP report was produced')
    evaluator=official_evaluation(output/'ground_truth.json',detections,ids,categories)
    evaluator.print_results()
    summary={key:float(value) for key,value in evaluator.get_results().items()}
    summary.update(model=str(args.model.resolve()),profile=args.profile,split=args.split,
        model_sha256=hashlib.sha256(args.model.read_bytes()).hexdigest(),
        manifest_sha256=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),
        image_count=len(images),mapped_model_classes=len(mapping),target_classes=len(categories),
        seconds_per_image_including_io=elapsed/len(images),imgsz=args.imgsz,
        caveat='Small pilot set is a workflow check; not evidence of production quality.' if args.profile=='pilot' else
               'Official LVIS metrics on selected images/categories; not a full LVIS benchmark score.')
    save_json(output/'summary.json',summary)
    precision=evaluator.eval['precision']  # IoU x recall x class x area
    recall=evaluator.eval['recall']        # IoU x class x area
    support={cid:{'images':set(),'boxes':0} for cid in sorted(categories)}
    for ann in gt['annotations']:
        support[ann['category_id']]['images'].add(ann['image_id'])
        support[ann['category_id']]['boxes']+=1
    def average(values):
        valid=values[values>=0]
        return float(valid.mean()) if valid.size else None
    per_class=[]
    ordered=evaluator.params.cat_ids
    labels={c['lvis_category_id']:c for c in manifest['classes']}
    for index,cid in enumerate(ordered):
        per_class.append({'english':labels[cid]['english'],'lvis_category_id':cid,
            'model_support':cid in mapping.values(), 'images':len(support[cid]['images']),
            'boxes':support[cid]['boxes'], 'AP50_95':average(precision[:,:,index,0]),
            'AP50':average(precision[0,:,index,0]),'AR300':average(recall[:,index,0]),
            'evidence':'insufficient' if len(support[cid]['images'])<20 else 'available'})
    save_json(output/'per_class.json',per_class)
    shared=[row for row in per_class if row['lvis_category_id'] in set(LEGACY_IDS.values()) and row['AP50_95'] is not None]
    summary['legacy_shared_classes_with_ground_truth']=len(shared)
    summary['legacy_shared_mean_AP50_95']=sum(row['AP50_95'] for row in shared)/len(shared) if shared else None
    summary['legacy_shared_category_ids']=[row['lvis_category_id'] for row in shared]
    save_json(output/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    main()
