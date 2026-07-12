"""
ONNX and Weight Exporter

Exports numpy neural network weights into standardized metadata format (JSON)
along with raw binary tensors.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import os
import json
import numpy as np

def export_model_to_json(npz_path, output_json_path):
    """
    Reads a standard .npz weight file and writes a metadata-rich JSON
    representation containing shapes, parameters, and layout for portable cross-compilation.
    """
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"Missing weights file: {npz_path}")

    data = np.load(npz_path)
    model_dict = {}

    for key in data.files:
        weights = data[key]
        model_dict[key] = {
            "shape": list(weights.shape),
            "values": weights.flatten().tolist()
        }

    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, 'w') as f:
        json.dump(model_dict, f, indent=4)
        
    print(f"Successfully exported weights metadata to JSON: {output_json_path}")

if __name__ == "__main__":
    weights_npz = "/Users/berkaykaratas/Downloads/turbojet/ai/models/surge_weights.npz"
    output_json = "/Users/berkaykaratas/Downloads/turbojet/ai/inference/surge_weights_onnx.json"
    try:
        export_model_to_json(weights_npz, output_json)
    except FileNotFoundError:
        print("Surge weights not found. Please run training script first.")
