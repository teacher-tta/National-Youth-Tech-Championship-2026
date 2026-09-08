"""
Usage:
    uv run train.py --data-dir data --epochs 15

Expects a directory structure like:
    data/
        object_a/
        object_b/
        none/
"""

import argparse
import json
import os

import torch
from torch import nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, models, transforms


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def build_model(num_classes):
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    for param in model.parameters():
        param.requires_grad = False
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


def main():
    parser = argparse.ArgumentParser(
        description="Train an image classifier with transfer learning."
    )
    parser.add_argument(
        "--data-dir", default="data", help="Directory of class subfolders"
    )
    parser.add_argument(
        "--output-dir", default="models", help="Where to save trained model files"
    )
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--image-size", type=int, default=224)
    args = parser.parse_args()

    device = get_device()
    print(f"Using device: {device}")

    train_transform = transforms.Compose(
        [
            transforms.Resize((args.image_size, args.image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    val_transform = transforms.Compose(
        [
            transforms.Resize((args.image_size, args.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    full_dataset = datasets.ImageFolder(args.data_dir, transform=train_transform)
    class_names = full_dataset.classes
    num_classes = len(class_names)
    print(
        f"Found {len(full_dataset)} images across {num_classes} classes: {class_names}"
    )

    val_size = max(1, int(len(full_dataset) * args.val_split))
    train_size = len(full_dataset) - val_size
    train_ds, val_ds = random_split(full_dataset, [train_size, val_size])
    # Validation subset should use non-augmented transforms. ImageFolder scans
    # directories in a fixed sorted order, so indices line up with full_dataset.
    val_ds.dataset = datasets.ImageFolder(args.data_dir, transform=val_transform)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)

    model = build_model(num_classes).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.classifier[1].parameters(), lr=args.lr)

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss, correct, total = 0.0, 0, 0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            correct += (outputs.argmax(1) == labels).sum().item()
            total += labels.size(0)

        train_loss = running_loss / total
        train_acc = correct / total

        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                val_correct += (outputs.argmax(1) == labels).sum().item()
                val_total += labels.size(0)
        val_acc = val_correct / val_total if val_total else 0.0

        print(
            f"Epoch {epoch}/{args.epochs}  "
            f"train_loss={train_loss:.4f}  train_acc={train_acc:.3f}  val_acc={val_acc:.3f}"
        )

    os.makedirs(args.output_dir, exist_ok=True)

    # Save class name <-> index mapping (index order matches model output)
    classes_path = os.path.join(args.output_dir, "classes.json")
    with open(classes_path, "w") as f:
        json.dump(class_names, f, indent=2)
    print(f"Saved class mapping to {classes_path}")

    model.eval()

    # Export TorchScript for quick testing on the Mac
    example_input = torch.rand(1, 3, args.image_size, args.image_size).to(device)
    traced = torch.jit.trace(model, example_input)
    ts_path = os.path.join(args.output_dir, "model.pt")
    traced.save(ts_path)
    print(f"Saved TorchScript model to {ts_path}")

    # Export ONNX for lightweight inference on the Pi (via onnxruntime)
    model_cpu = model.to("cpu")
    example_input_cpu = torch.rand(1, 3, args.image_size, args.image_size)
    onnx_path = os.path.join(args.output_dir, "model.onnx")
    torch.onnx.export(
        model_cpu,
        example_input_cpu,
        onnx_path,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
        opset_version=12,
    )
    print(f"Saved ONNX model to {onnx_path}")

    print("\nDone. Copy the ONNX model + class file to the Pi with, e.g.:")
    print(f"  scp {onnx_path} {classes_path} pi@raspberrypi.local:/home/pi/models/")


if __name__ == "__main__":
    main()
