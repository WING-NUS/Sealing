import numpy as np
from .video_base_dataset import BaseDataset
import os
import json
import pandas as pd
import h5py, torch


class MSRVTTQADataset(BaseDataset):
    def __init__(self, *args, split="", **kwargs):
        assert split in ["train", "val", "test"]
        #         if split == "test":
        #             split = "val"
        self.split = split
        self.metadata = None
        self.ans_lab_dict = None
        if split == "train":
            names = ["msrvtt_qa_train"]
            # names = ["msrvtt_qa_train", "msrvtt_qa_val"]
        elif split == "val":
            names = ["msrvtt_qa_test"]  # ["msrvtt_qa_val"]
        elif split == "test":
            names = ["msrvtt_qa_test"]  # vqav2_test-dev for test-dev

        super().__init__(
            *args,
            **kwargs,
            names=names,
            text_column_name="questions",
            remove_duplicate=False,
        )
        self.names = names
        # self.num_frames = 4
        self._load_metadata()

    def _load_metadata(self):
        self.metadata_dir = metadata_dir = './DataSet/msrvtt'
        split_files = {
            'train': 'msrvtt_qa_train.jsonl',
            'val': 'msrvtt_qa_val.jsonl',
            'test': 'msrvtt_qa_test.jsonl'
        }
        answer_fp = os.path.join(metadata_dir, 'ans2label.json')  # 1500 in total (all classes in train)
        mapping_fp = os.path.join(metadata_dir, 'processed/vidmapping.json')
        
        self.ans_lab_dict = json.load(answer_fp)
        self.vidmapping = json.load(mapping_fp)
        with open(answer_fp, 'r') as JSON:
            self.ans_lab_dict = json.load(JSON)
            
        for name in self.names:
            split = name.split('_')[-1]
            target_split_fp = split_files[split]
            # path_or_buf=os.path.join(metadata_dir, target_split_fp)
            metadata = pd.read_json(os.path.join(metadata_dir, target_split_fp), lines=True)
            if self.metadata is None:
                self.metadata = metadata
            else:
                self.metadata.update(metadata)
        print("total {} samples for {}".format(len(self.metadata), self.names))
        # data1.update(data2)

    def get_text(self, sample):
        text = sample['question']
        encoding = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_text_len,
            return_special_tokens_mask=True,
        )
        return (text, encoding)

    def get_answer_label(self, sample):
        text = sample['answer']
        ans_total_len = len(self.ans_lab_dict) + 1  # one additional class
        try:
            ans_label = self.ans_lab_dict[text]  #
        except KeyError:
            ans_label = -100  # ignore classes
            # ans_label = 1500 # other classes
        scores = np.zeros(ans_total_len).astype(int)
        scores[ans_label] = 1
        return text, ans_label, scores
        # return text, ans_label_vector, scores

    def __getitem__(self, index):
        with h5py.File(os.path.join(self.metadata_dir, 'processed/msrvtt_qa_video_feat.h5'), 'r') as f:
            sample = self.metadata.iloc[index]
            qid = index
            vid = self.vidmapping[sample['video']]
            
            frames = f['sampled_frames'][vid].reshape(1, 3, 3, 224, 224)
            image_tensor = torch.Tensor(frames)
            text = self.get_text(sample)
            if self.split != "test":
                answers, labels, scores = self.get_answer_label(sample)
            else:
                answers = list()
                labels = list()
                scores = list()

        return {
            "image": image_tensor,
            "text": text,
            "vqa_answer": answers,
            "vqa_labels": labels,
            "vqa_scores": scores,
            "qid": qid,
        }

    def __len__(self):
        return len(self.metadata)