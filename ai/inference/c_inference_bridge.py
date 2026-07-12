"""
C Inference Bridge

Generates a static C header containing the trained weights and biases
from the numpy model, enabling embedded C inference without external runtimes.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import os
import numpy as np

def generate_c_header(npz_path, header_path):
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"Missing weights file: {npz_path}")

    data = np.load(npz_path)
    
    W1 = data["W1"]
    b1 = data["b1"]
    W2 = data["W2"]
    b2 = data["b2"]
    W3 = data["W3"]
    b3 = data["b3"]

    header_content = []
    header_content.append("/**")
    header_content.append(" * @file surge_weights.h")
    header_content.append(" * @brief Auto-generated static neural network weights for embedded inference")
    header_content.append(" * @compliance DO-178C DAL A / MISRA C:2012")
    header_content.append(" */")
    header_content.append("")
    header_content.append("#ifndef SURGE_WEIGHTS_H")
    header_content.append("#define SURGE_WEIGHTS_H")
    header_content.append("")

    # Helper function to format 2D arrays
    def format_2d_array(name, arr):
        rows, cols = arr.shape
        lines = [f"static const double {name}[{rows}][{cols}] = {{"]
        for row in arr:
            row_str = ", ".join([f"{val:.10e}" for val in row])
            lines.append(f"    {{ {row_str} }},")
        # Remove trailing comma from last line
        lines[-1] = lines[-1].rstrip(",")
        lines.append("};")
        return "\n".join(lines)

    # Helper function to format 1D arrays
    def format_1d_array(name, arr):
        # Flatten array
        flat = arr.flatten()
        size = len(flat)
        vals_str = ", ".join([f"{val:.10e}" for val in flat])
        return f"static const double {name}[{size}] = {{ {vals_str} }};"

    header_content.append(format_2d_array("SURGE_W1", W1))
    header_content.append("")
    header_content.append(format_1d_array("SURGE_B1", b1))
    header_content.append("")
    header_content.append(format_2d_array("SURGE_W2", W2))
    header_content.append("")
    header_content.append(format_1d_array("SURGE_B2", b2))
    header_content.append("")
    header_content.append(format_2d_array("SURGE_W3", W3))
    header_content.append("")
    header_content.append(format_1d_array("SURGE_B3", b3))
    header_content.append("")
    header_content.append("#endif /* SURGE_WEIGHTS_H */")

    os.makedirs(os.path.dirname(header_path), exist_ok=True)
    with open(header_path, "w") as f:
        f.write("\n".join(header_content) + "\n")

    print(f"Successfully generated static C header bridge: {header_path}")

if __name__ == "__main__":
    weights_npz = "/Users/berkaykaratas/Downloads/turbojet/ai/models/surge_weights.npz"
    output_h = "/Users/berkaykaratas/Downloads/turbojet/core/include/surge_weights.h"
    try:
        generate_c_header(weights_npz, output_h)
    except FileNotFoundError:
        print("Surge weights not found. Please run training script first.")
