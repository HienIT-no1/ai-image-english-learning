"""Check the errors that previously caused data corruption or false learning."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prepare import select_images, xywh_to_yolo


class DatasetTests(unittest.TestCase):
    def test_boxes_clip_and_normalize_without_swapping_axes(self):
        self.assertEqual(xywh_to_yolo([-5,10,25,40],100,200),(.1,.15,.2,.2))
        with self.assertRaises(ValueError):
            xywh_to_yolo([200,10,5,5],100,200)
        with self.assertRaises(ValueError):
            xywh_to_yolo([float('nan'),10,5,5],100,200)

    def test_partial_annotations_never_become_verified_negatives(self):
        images=[{'id':i,'width':100,'height':100,'coco_url':f'http://images.cocodataset.org/train2017/{i:012}.jpg',
                 'neg_category_ids':[3],'not_exhaustive_category_ids':[2]} for i in range(1,9)]
        anns=[{'image_id':i,'category_id':cid,'bbox':[1,2,20,30]} for i in range(1,9) for cid in [1,2]]
        selected=select_images(images,anns,{1,2,3,4},{'train':2},'train')['train']
        self.assertTrue(selected)
        for image in selected:
            self.assertEqual(image['verified_categories'],[1,3])
            self.assertEqual(len(image['annotations']),2)

    def test_validation_test_split_is_deterministic_and_disjoint(self):
        images=[{'id':i,'width':100,'height':100,'coco_url':f'http://images.cocodataset.org/val2017/{i:012}.jpg'} for i in range(1,80)]
        anns=[{'image_id':i,'category_id':1,'bbox':[0,0,10,10]} for i in range(1,80)]
        first=select_images(images,anns,{1},{'val':5,'test':5},'val')
        self.assertEqual(first,select_images(images,anns,{1},{'val':5,'test':5},'val'))
        self.assertFalse({r['image_id'] for r in first['val']} & {r['image_id'] for r in first['test']})


class LossTests(unittest.TestCase):
    def test_real_1000_class_detector_backpropagates_finite_loss(self):
        import torch
        from ultralytics.cfg import get_cfg
        from ultralytics.nn.tasks import DetectionModel
        from verified_training import VerifiedLoss
        torch.set_num_threads(2)
        model=DetectionModel('yolo11n.yaml',nc=1000,verbose=False)
        model.args=get_cfg()
        batch={'img':torch.rand(2,3,64,64),'batch_idx':torch.tensor([0,1]),
               'cls':torch.tensor([[0.],[999.]]),
               'bboxes':torch.tensor([[.5,.5,.4,.4],[.4,.4,.3,.3]]),
               'verified_classes':torch.zeros((2,1000),dtype=torch.bool)}
        model.train()
        loss,_=VerifiedLoss(model)(model(batch['img']),batch)
        self.assertTrue(torch.isfinite(loss).all())
        loss.sum().backward()
        self.assertTrue(any(p.grad is not None and p.grad.abs().sum()>0 for p in model.parameters()))

    def test_unknown_classes_have_zero_gradient_but_positive_anchors_learn(self):
        import torch
        from verified_training import VerifiedBCE
        logits=torch.zeros((1,2,3),requires_grad=True)
        target=torch.tensor([[[1.,0.,0.],[0.,1.,0.]]])
        criterion=VerifiedBCE()
        criterion.known=torch.tensor([[True,False,False]])
        criterion(logits,target).sum().backward()
        self.assertLess(logits.grad[0,0,0].item(),0)
        self.assertGreater(logits.grad[0,1,0].item(),0)
        self.assertLess(logits.grad[0,1,1].item(),0)
        self.assertEqual(logits.grad[0,0,1].item(),0)
        self.assertTrue(torch.equal(logits.grad[:,:,2],torch.zeros((1,2))))

    def test_missing_verification_mask_stops_training(self):
        import torch
        from verified_training import VerifiedBCE
        with self.assertRaises(RuntimeError):
            VerifiedBCE()(torch.zeros((1,2,3)),torch.zeros((1,2,3)))


class EvaluationTests(unittest.TestCase):
    def test_comparison_uses_the_same_manifest_and_shared_classes(self):
        from assess import compare_reports
        settings={'profile':'full','split':'val','imgsz':640,'manifest_sha256':'same-data',
                  'image_count':30,'target_classes':1000}
        old=[{'lvis_category_id':12,'english':'apple','AP50_95':.2,'model_support':True},
             {'lvis_category_id':34,'english':'backpack','AP50_95':.4,'model_support':True}]
        new=[{**old[0],'AP50_95':.4},{**old[1],'AP50_95':.5}]
        result=compare_reports(settings,settings,new,old)
        self.assertEqual(result['shared_class_count'],2)
        self.assertAlmostEqual(result['shared_AP_gain'],.15)
        self.assertTrue(result['improved_on_shared_validation'])
        with self.assertRaises(ValueError):
            compare_reports(settings,{**settings,'manifest_sha256':'different-data'},new,old)

    def test_image_list_cannot_turn_into_one_large_gpu_batch(self):
        from evaluate import predict_individually
        class Model:
            def __init__(self): self.largest_batch=0
            def predict(self,source,**options):
                self.largest_batch=max(self.largest_batch,len(source) if isinstance(source,list) else 1)
                return iter([source])
        model=Model()
        paths=[f'{i}.jpg' for i in range(432)]
        self.assertEqual(list(predict_individually(model,paths)),paths)
        self.assertEqual(model.largest_batch,1)

    def test_official_lvis_ignores_an_unverified_category_prediction(self):
        from evaluate import official_evaluation
        fixture={'images':[{'id':1,'width':100,'height':100,'neg_category_ids':[],
                            'not_exhaustive_category_ids':[]}],
                 'categories':[{'id':1,'name':'apple','frequency':'f'},{'id':2,'name':'cup','frequency':'f'}],
                 'annotations':[{'id':1,'image_id':1,'category_id':1,'bbox':[10,10,20,20],
                                 'area':400,'segmentation':[[10,10,30,10,30,30,10,30]]}]}
        predictions=[{'image_id':1,'category_id':1,'bbox':[10,10,20,20],'score':.9},
                     {'image_id':1,'category_id':2,'bbox':[50,50,10,10],'score':.99}]
        path=Path(__file__).resolve().parents[1]/'reports/lvis-test/gt.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(fixture),encoding='utf-8')
        evaluator=official_evaluation(path,predictions,{1},{1,2})
        self.assertAlmostEqual(float(evaluator.get_results()['AP']),1.0,places=5)


if __name__=='__main__':
    unittest.main()
