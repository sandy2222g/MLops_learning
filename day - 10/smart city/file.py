import os
import shutil
import random

# paths
image_dir = r"D:\smartcity_dataset\outputdir"
label_dir = r"D:\smartcity_dataset\outputdir"

output_dir = r"D:\smart city\classified_dataset"

# create folders
splits = ["train", "val", "test"]
classes = ["safe", "warning", "danger"]

for split in splits:
    for cls in classes:
        os.makedirs(
            os.path.join(output_dir, split, cls),
            exist_ok=True
        )

# collect classified images
data = {
    "safe": [],
    "warning": [],
    "danger": []
}

# read labels
for txt_file in os.listdir(label_dir):

    if not txt_file.endswith(".txt"):
        continue

    txt_path = os.path.join(label_dir, txt_file)

    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read().lower()

    # priority
    if "danger" in content:
        cls = "danger"

    elif "warning" in content:
        cls = "warning"

    else:
        cls = "safe"

    base_name = os.path.splitext(txt_file)[0]

    image_path = None

    # image extensions
    for ext in [".jpg", ".png", ".jpeg"]:

        temp = os.path.join(image_dir, base_name + ext)

        if os.path.exists(temp):
            image_path = temp
            break

    if image_path is None:
        print(f"Image missing for {txt_file}")
        continue

    data[cls].append(image_path)

# split ratios
train_ratio = 0.7
val_ratio = 0.2
test_ratio = 0.1

# split and copy
for cls in classes:

    images = data[cls]

    random.shuffle(images)

    total = len(images)

    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)

    train_files = images[:train_end]
    val_files = images[train_end:val_end]
    test_files = images[val_end:]

    split_map = {
        "train": train_files,
        "val": val_files,
        "test": test_files
    }

    for split, files in split_map.items():

        for file_path in files:

            dest = os.path.join(
                output_dir,
                split,
                cls,
                os.path.basename(file_path)
            )

            shutil.copy(file_path, dest)

print("Dataset preparation completed")