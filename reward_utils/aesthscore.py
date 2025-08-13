from PIL import Image
import io
import numpy as np
import torch
from collections import defaultdict
import os
from importlib import resources
import torch
import torch.nn as nn
import numpy as np
from transformers import CLIPModel, CLIPProcessor
from PIL import Image

ASSETS_PATH = __file__.replace(".py","")


class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(768, 1024),
            nn.Dropout(0.2),
            nn.Linear(1024, 128),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.Dropout(0.1),
            nn.Linear(64, 16),
            nn.Linear(16, 1),
        )

    @torch.no_grad()
    def forward(self, embed):
        return self.layers(embed)


class AestheticScorer(torch.nn.Module):
    def __init__(self, dtype):
        super().__init__()
        self.clip = CLIPModel.from_pretrained("openai/clip-vit-large-patch14")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")
        self.mlp = MLP()
        state_dict = torch.load(
            os.path.join(ASSETS_PATH,"sac+logos+ava1-l14-linearMSE.pth")
        )
        self.mlp.load_state_dict(state_dict)
        self.dtype = dtype
        self.eval()

    @torch.no_grad()
    def __call__(self, images):
        device = next(self.parameters()).device
        inputs = self.processor(images=images, return_tensors="pt")
        inputs = {k: v.to(self.dtype).to(device) for k, v in inputs.items()}
        embed = self.clip.get_image_features(**inputs)
        # normalize embedding
        embed = embed / torch.linalg.vector_norm(embed, dim=-1, keepdim=True)
        return self.mlp(embed).squeeze(1)


def create_model(device=None):
    if device is None:
        device = torch.device('cuda' if (torch.cuda.is_available()) else 'cpu')
    scorer = AestheticScorer(dtype=torch.float32).to(device)
    return scorer

def aesthetic_score(images, model=None):
    if model is None:
        model=create_model()
    if isinstance(images, torch.Tensor):
        images = (images * 255).round().clamp(0, 255).to(torch.uint8)
    else:
        images = images.transpose(0, 3, 1, 2)  # NHWC -> NCHW
        images = torch.tensor(images, dtype=torch.uint8)
    scores = model(images)
    return scores, model